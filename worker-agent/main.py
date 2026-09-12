import json
import uuid
import requests
import os
import uuid
import requests
import subprocess
from datetime import datetime
import hashlib
from contracts.inference_contracts.evidence import Evidence
from pathlib import Path
from typing import Any, overload, Mapping, List, Dict, Iterable, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass
from ollama import ResponseError 
from collections import deque
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)
from langchain_core.tools import tool
from langchain_ollama import ChatOllama



import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ddgs import DDGS
import asyncio
from playwright.async_api import async_playwright
import nest_asyncio



class ToolEvent(BaseModel):
    iteration: int
    event_type: str
    tool: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )




# ---------------------------------------------------------------------------
# Helper: send a tool result to the evidence ingestion endpoint
# ---------------------------------------------------------------------------

def ingest_tool_event(execution_id: str, tool_event: ToolEvent) -> None:
  
    try:
    
        now = datetime.utcnow()
         
        payload = Evidence(
            evidence_id=str(uuid.uuid4()),
            execution_id=execution_id,
            event_id=f"{execution_id}-{tool_event.iteration}",
            evidence_type=tool_event.tool,          # e.g. "web_search", "read_file"
            content=str(tool_event.result),         # jam for now, per your call
            source_type=tool_event.event_type,
            source_name=tool_event.tool,
            observed_at=now,
            retrieved_at=now,
            metadata={"args": tool_event.args},     # structured, don't lose it
            worker_version=1.0,
        )
        resp = requests.post("http://fastapi:8000/ingest/evidence", json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[Evidence ingestion] failed for event {event_id}: {e}")


# Apply the patch to allow nested event loops inside the Jupyter runtime environment
nest_asyncio.apply()
from importlib.metadata import version

for package in [
    "langchain",
    "langchain-core",
    "langchain-ollama",
]:
    print(package, version(package))

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://10.42.0.192:11434/",
)

MODEL_NAME = os.getenv( "GEN_MODEL", "gpt-oss:20b")
DISTILL_MODEL_NAME = os.getenv( "DISTILL_GEN_MODEL", "gpt-oss:20b")

llm = ChatOllama(
    model=MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    temperature=0.01,
    num_ctx=40960,
)
distillation_llm = ChatOllama(
    model=DISTILL_MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    temperature=0.01,
    num_predict=5000,  # distillation JSON should never need more than this
)
print(f"Using {MODEL_NAME} at {OLLAMA_BASE_URL}")
print(f"Distilling with {DISTILL_MODEL_NAME} at {OLLAMA_BASE_URL}")


response = llm.invoke("Reply with exactly: Ollama connection works")
print(response.content)

WORKSPACE_PATH = os.getenv(
    "WORKSPACE",
    "/agentworkspace",
)
WORKSPACE = Path(WORKSPACE_PATH)

WORKSPACE.mkdir(parents=True, exist_ok=True)

WORKSPACE = WORKSPACE.resolve()
print(WORKSPACE)


EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", ".mypy_cache", ".ruff_cache"}

def safe_path(relative_path: str) -> Path:
    """
    Resolve a user-provided path inside WORKSPACE.
    Prevents paths such as ../../etc/passwd.
    """
    path = (WORKSPACE / relative_path).resolve()

    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"Path escapes workspace: {relative_path}")

    return path



@tool
def web_search(query: str) -> str:
    """Executes a keyword search on the live internet via DuckDuckGo.
    Use this first to find relevant URLs and snippets when asked about
    current events, weather, news, or fresh updates.

    Args:
        query: A standard web search keyword query.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Error: The provided search query was empty."

    try:
        # Initializing DuckDuckGo Search Client
        with DDGS() as ddgs:
            # Gather up to 4 clean results to reduce token clutter
            raw_results = list(ddgs.text(clean_query, max_results=4))

        if not raw_results:
            return f"Search completed, but no results were found for: '{clean_query}'"

        structured_results = []
        for item in raw_results:
            structured_results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("href", ""),
                "snippet": item.get("body", "No description available.")
            })

        return json.dumps({"results": structured_results}, indent=2)

    except Exception as e:
        return f"Error: The DuckDuckGo search operation failed: {str(e)}"



@tool
def web_fetch(url: str) -> str:
    """Visits a specific URL found from a web search using a headless browser 
    to extract its main text. Use this tool ONLY after finding a trusted URL 
    from a web search when you need deeper information than the short snippet provided.
    
    Args:
        url: The absolute web address (including http/https).
    """
    # 1. SSRF Guardrails: Prevent local network scanning inside the Docker bridge
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        return "Error: Invalid URL protocol or missing host domain."
    
    if any(ip in parsed_url.netloc for ip in ["localhost", "127.0.0.1", "0.0.0.0"]):
        return "Error: Accessing internal container network addresses is prohibited."

    # Define an internal async function to cleanly wrap Playwright's async API
    async def _fetch():
        async with async_playwright() as p:
            # Launch Chromium with system sandboxing optimizations for Docker
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled", # Evade automated tracking flags
                    "--no-sandbox",                                 # Required for root execution inside Docker
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",                      # Use disk swap to avoid shared evidence engine crashes
                    "--disable-infobars"
                ]
            )
            
            # Establish baseline organic Windows Chrome fingerprint profile
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
                locale="en-US"
            )
            
            page = await context.new_page()
            
            # Inline JS variable injection to hide automation signatures
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Execute the request with search engine referer masking
            response = await page.goto(
                url, 
                timeout=15000, 
                wait_until="domcontentloaded",
                referer="https://google.com"
            )
            
            if not response:
                await browser.close()
                return "Error: Headless browser failed to establish a network connection."
                
            if response.status == 403:
                await browser.close()
                return "Error 403: Forbidden. The website blocked automated access, even via browser emulation."
            elif response.status == 404:
                await browser.close()
                return "Error 404: Webpage not found."

            # Brief delay to allow background cryptographic script challenges to clear (e.g. Cloudflare)
            await page.wait_for_timeout(1500)
            
            html_content = await page.content()
            await browser.close()
            return html_content

    try:
        # Run the async crawler safely within our single-threaded loop architecture
        html_content = asyncio.run(_fetch())
        
        # 2. Content extraction with layout cleanup
        soup = BeautifulSoup(html_content, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "form", "iframe"]):
            element.decompose()

        text_blocks = []
        for p in soup.find_all(["p", "h1", "h2", "h3", "li"]):
            text = p.get_text().strip()
            if len(text) > 20: 
                text_blocks.append(text)

        full_text = "\n".join(text_blocks)
        
        # Keep agent parsing snappy and inside context token window boundaries
        if len(full_text) > 4000:
            return full_text[:4000] + "\n\n[Content truncated by assistant framework for token safety...]"
        
        return full_text if full_text.strip() else "Error: Target webpage reached, but no layout text could be isolated."

    except Exception as e:
        return f"Error: Web fetch exception encountered during execution: {str(e)}"
        

def _is_binary(file: Path, sample_size: int = 1024) -> bool:
    try:
        with open(file, "rb") as f:
            return b"\x00" in f.read(sample_size)
    except Exception:
        return True

@tool
def search_file(path: str, query: str) -> str:
    """
    Search a local file or all files under a directory for an **exact** text match.

    Parameters
    ----------
    path : str
        Path to the file or directory to search (relative to the workspace or absolute).
    query : str
        The exact text to look for (case‑sensitive).

    Returns
    -------
    str
        JSON array of objects, each with:
            * `file` – relative file path (empty string for single‑file mode)
            * `line` – 1‑based line number
            * `text` – the line content (trimmed of trailing newline)

        If the path does not exist or is not a file/directory, a short error message is returned instead of JSON.
        When no matches are found an empty JSON array (`[]`) is returned.

    Notes
    -----
    * The file(s) are read with UTF‑8 encoding; if decoding fails,
      the fallback encoding `latin‑1` is used.
    * To keep the agent’s context small, the search stops after
      `max_hits` matches per file (default 10).
    * Very large files (over `max_chars` bytes) are truncated before
      searching; the truncated text ends with `"\n...[truncated]"`.
    """
    
    target_path = safe_path(path)

    if not target_path.exists():
        return f"Path does not exist: {path}"

    def _search_single(file: Path) -> List[Dict[str, str]]:
        if _is_binary(file):
            return []
        try:
            content = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = file.read_text(encoding="latin-1")

        max_chars = 30_000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n...[truncated]"

        matches: List[Dict[str, str]] = []
        max_hits = 10
        for i, line in enumerate(content.splitlines(), start=1):
            if query in line:
                matches.append({"file": str(file.relative_to(WORKSPACE)), "line": i, "text": line.strip()})
                if len(matches) >= max_hits:
                    break
        return matches

    results: List[Dict[str, str]] = []
    max_total_hits = 50

    if target_path.is_file():
        results.extend(_search_single(target_path))
    else:
        for file in sorted(target_path.rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(WORKSPACE)
            if any(part in EXCLUDED_DIRS for part in relative.parts):
                continue
            results.extend(_search_single(file))
            if len(results) >= max_total_hits:
                break

    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def list_files() -> str:
    """List files and directories in the current project workspace."""
    entries = []
    for path in sorted(WORKSPACE.rglob("*")):
        relative = path.relative_to(WORKSPACE)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{relative}{suffix}")
    return "\n".join(entries) if entries else "(workspace is empty)"
    
@tool
def read_file(
    path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None
) -> str:
    """
    Read a UTF‑8 text file from the project workspace.

    Parameters
    ----------
    path : str
        Path to the file (relative or absolute).
    line_start : int | None, default None
        First line to return (1‑based).  If omitted, start at the beginning.
    line_end : int | None, default None
        Last line to return (inclusive).  If omitted, go to the end.

    Returns
    -------
    str
        The requested content (possibly truncated to 30 k chars).
        If the file does not exist or is not a file, a short error string is returned.
    """
    # Resolve path safely
    file_path = safe_path(path)

    # Basic checks
    if not file_path.exists():
        return f"File does not exist: {path}"
    if not file_path.is_file():
        return f"Not a file: {path}"

    # Read the file – try UTF‑8, fall back to latin‑1
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    # Optionally slice by line numbers
    if line_start is not None or line_end is not None:
        lines = content.splitlines()
        # Normalize missing values
        start = line_start - 1 if line_start is not None else 0
        end   = line_end   if line_end   is not None else len(lines)
        # Guard against bad indices
        if start < 0 or end < start:
            return "Invalid line range specified."
        # Slice and re‑join
        content = "\n".join(lines[start:end])

    # Truncate very large output
    max_chars = 30_000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n...[truncated]"

    return content


@tool
def write_file(path: str, content: Any, overwrite: bool = False) -> str:
    """
    Write `content` to `path`.  
    - If the file exists and `overwrite` is False (default), the call is a no‑op
      and you get a short “file exists” message.
    - If `overwrite` is True, the existing file is simply replaced.
    - `content` may be:
        • a mapping → pretty‑printed JSON (unless it contains a single string)
        • a string → written verbatim (real newlines, no `\\n`)

    Returns a human‑readable status message.
    """

    file_path = safe_path(path)

    if isinstance(content, Mapping):
        if "content" in content and isinstance(content["content"], str):
            content_str = content["content"]
        else:
            content_str = json.dumps(content, indent=2, ensure_ascii=False)
    elif isinstance(content, str):
        content_str = content
    else:
        raise TypeError(f"Unsupported content type {type(content)}")

    if file_path.exists() and not overwrite:
        return (
            f"File already exists: {path}. "
            "Use `overwrite=True` to replace it or use `read_file` + "
            "`edit_file` to modify it."
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content_str, encoding="utf-8")
    return (
        f"Created {len(content_str)} characters in "
        f"{file_path.relative_to(WORKSPACE_PATH)}"
    )


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Edit a UTF-8 text file by replacing one exact occurrence of old_text
    with new_text.

    The file must already exist. The replacement is intentionally limited
    to one occurrence so the agent cannot accidentally modify multiple
    unrelated sections.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return f"File does not exist: {path}"

    if not file_path.is_file():
        return f"Not a file: {path}"

    content = file_path.read_text(encoding="utf-8")

    occurrences = content.count(old_text)

    if occurrences == 0:
        return (
            f"Could not edit {path}: old_text was not found. "
            "Read the file again and use an exact text match."
        )

    if occurrences > 1:
        return (
            f"Could not edit {path}: old_text occurs {occurrences} times. "
            "Provide a larger, more specific old_text block."
        )

    updated_content = content.replace(old_text, new_text, 1)
    file_path.write_text(updated_content, encoding="utf-8")

    return (
        f"Edited {file_path.relative_to(WORKSPACE)}: "
        f"replaced {len(old_text)} characters with {len(new_text)} characters."
    )



@tool
def run_command(command: str) -> str:
    """
    Run a non-interactive shell command inside the project workspace.
    Use this for formatting, tests, compilation, and inspection.
    """
    blocked_fragments = [
        "rm -rf",
        "shutdown",
        "reboot",
        "mkfs",
        "dd if=",
        ":(){",
        "curl | sh",
        "wget | sh",
    ]

    normalized = command.lower().replace(" ", "")
    for fragment in blocked_fragments:
        if fragment.replace(" ", "") in normalized:
            return f"Blocked potentially destructive command: {command}"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=60,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
            },
        )

        output = (
            f"exit_code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        if len(output) > 20_000:
            output = output[:20_000] + "\n...[output truncated]"

        return output

    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as exc:
        return f"Command failed to run: {type(exc).__name__}: {exc}"


TOOLS = [
    list_files,
    read_file,
    write_file,
    edit_file,
    search_file,
    run_command,
    web_search,
    web_fetch,
]


TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}

for item in TOOLS:
    print(item.name)



llm_with_tools = llm.bind_tools(TOOLS)


response = llm_with_tools.invoke(
    "Use the list_files tool and report the files in the workspace."
)

print("content:", response.content)
print("tool calls:", response.tool_calls)


DISTILLATION_PROMPT = """
The Year is 2026, You are Graph‑Partner, an AI collaborator specialized in distilling threads of work on a semantic‑web/OWL knowledge‑graph stack that runs locally on a Linux server with an NVIDIA RTX 5070 GPU.

You are part of an agent pipeline that extracts facts from a thread

the next iteration will use your distillation to guide work and manage token context

you will be given the initial user prompt, followed by everything currently in the thread context, which may contain an earlier iteration of your distillation results as the third message in the series.

when the context already contains your earlier distillation result, the distillation may include information from messages that have been truncated from the context

if the third message describes a tool call, we are on the first distillation pass for this thread

use the information from the context to infer the progress of the thread and help form the direction of the tool enabled agent

output **only** a single JSON object with these top‑level keys:
  - artifacts:   [{ "id":"", "type":"", "value":"" }]  #only keep important parts of artifacts, not whole files
  - claims:      [{ "statement":"", "source":"", "confidence":0‑1 }] #claims based on agent tools not the human prompt
  - understandings:[{ "concept":"", "detail":""}]
  - hypotheses:  [{ "hypothesis":"", "status":"pending/confirmed/ruled‑out", "confidence":0‑1 }]
  - completed_steps:   [{ "step":"", "result":""}] #try to prevent looping
  - todo_steps:   [{ "step":"", "deadline":"YYYY‑MM‑DD"}] #intent

If a key has no entries, use an empty array.
**Do NOT** wrap the output in Markdown or quotes around keys.
your response must be less than 3000 chars
Make sure the JSON is syntactically valid (no trailing commas, proper quoting).

"""


SYSTEM_PROMPT = """
The Year is 2026, You are Graph‑Partner, an AI collaborator specialized in building, deploying, and iterating on a semantic‑web/OWL knowledge‑graph stack that runs locally on a Linux server with an NVIDIA RTX 5070 GPU.

Your primary mission is to help the user (a 48‑year‑old software engineer) create a **self‑sustaining, compute‑backbone** that powers a “human + AI” ecosystem.  You must:

1. **Stay Technical, No Job‑Search Talk**
   • Skip any corporate‑HR or job‑search advice.
   • Focus on concrete tooling, code, and deployment steps.

2. **Lead with the OWL Inference Flow**
   • Explain, build, and maintain an OWL ontology, RDF data, and a forward‑chaining reasoner.
   • Show how to expose this through SPARQL and/or GraphQL, then hook it to a local LLM (Ollama / vLLM).

3. **Give Hands‑On, Code‑Ready Guidance**
   • Provide Docker‑Compose files, shell scripts, Python snippets, and Jena/GraphDB commands.
   • Offer sanity‑check templates (e.g., “verify that inferred triples appear in SPARQL results”).

4. **Maintain an Iterative Loop**
   • After each step, ask a “quick check” question (e.g., “Did the reasoner add the inferred triple?”).
   • Suggest metrics to capture (token‑rate, query latency, GPU utilization) and how to log them.

5. **Ask Clarifying Questions When Needed**
   • If any environmental detail is missing (e.g., Docker version, data location, existing ontology files), ask for it.
   • Do not bombard with questions; one or two targeted ones per turn are enough.

6. **Use a Friendly, Future‑Oriented Tone**
   • Encourage experimentation, celebrate small wins, and keep the user motivated.
   
You are not allowed to declare success without recording evidence.

Current World Model:
- Inspect existing files.
- Use write_file to create example implementations.
- use web_search to search the web
- use web_fetch to call individual web locations
- use search_file to get local workspace file lines matching search criteria
- Use edit_file for targeted modifications to existing files, modify anything you need to in the workspace.
- Use read_file to inspect relevant files before editing them.
- When using edit_file, provide an exact old_text match and a precise new_text replacement.
- If an edit_file operation fails because old_text was not found or is ambiguous, read or search the file again before retrying.
- Use run_command for command line tools, tests, formatters, linters, compilers, and basic inspection.
- Do not claim that code works unless you actually run an appropriate check.
- Keep generated code focused and maintainable.
- exit for more information only when the requirement is genuinely ambiguous.
- Do not delete or overwrite unrelated files.
- All paths must be relative to the project workspace.

If the task cannot be completed without making an architectural decision not specified by the prompt, stop and explain the decision instead of guessing.

the tool calling system you interact with requires that you respond with tool_calls or content, respond with only content to signal to the user that you are done, 
include  prompts for continued work on ideas that you find interesting

"""

# ------------------------------------------------------------------
# 0️⃣  Helpers
# ------------------------------------------------------------------
SUMMARY_TAG = "__DISTILLED_SUMMARY__"  # sentinel prefix, not inferred from position/type

def make_summary_message(facts: dict) -> HumanMessage:
    return HumanMessage(content=SUMMARY_TAG + json.dumps(facts, indent=2))

def is_summary_message(msg: BaseMessage) -> bool:
    return isinstance(msg, HumanMessage) and msg.content.startswith(SUMMARY_TAG)


def truncate_history(
    messages: List[BaseMessage],
    max_tokens: int = 25_000,
    tokenizer=None,
    preserve: int = 2,
) -> List[BaseMessage]:
    """
    Preserve the first `preserve` messages and retain the newest complete
    conversation units that fit within `max_tokens`.

    Conversation units include:

    - an AI tool-call message plus its following ToolMessages;
    - an invalid AI response plus the following correction HumanMessage;
    - ordinary messages;
    - consecutive tool messages attached to the preceding AI message.
    """

    if len(messages) <= preserve:
        return messages.copy()

    kept_first = messages[:preserve]
    rest = messages[preserve:]

    def is_tool_call_message(msg: BaseMessage) -> bool:
        return (
            isinstance(msg, AIMessage)
            and bool(getattr(msg, "tool_calls", None))
        )

    def is_invalid_response_pair_start(
        index: int,
        items: List[BaseMessage],
    ) -> bool:
        """
        Treat AIMessage followed by HumanMessage as a recovery pair only
        when the human message looks like a retry/correction instruction.
        """
        if index + 1 >= len(items):
            return False

        current = items[index]
        following = items[index + 1]

        if not isinstance(current, AIMessage):
            return False

        if not isinstance(following, HumanMessage):
            return False

        text = str(following.content).lower()

        recovery_markers = (
            "invalid",
            "parse",
            "parser",
            "tool call",
            "tool-call",
            "retry",
            "previous response",
            "could not be parsed",
        )

        return any(marker in text for marker in recovery_markers)

    # Build atomic units.
    units: List[List[BaseMessage]] = []
    i = 0

    while i < len(rest):
        msg = rest[i]

        # Failed AI output followed by a correction request.
        if is_invalid_response_pair_start(i, rest):
            units.append([rest[i], rest[i + 1]])
            i += 2
            continue

        # AI tool call plus all immediately following ToolMessages.
        if is_tool_call_message(msg):
            unit = [msg]
            i += 1

            while i < len(rest) and isinstance(rest[i], ToolMessage):
                unit.append(rest[i])
                i += 1

            units.append(unit)
            continue

        # A stray ToolMessage should remain attached to the preceding unit
        # if possible rather than becoming an independent conversation turn.
        if isinstance(msg, ToolMessage) and units:
            units[-1].append(msg)
            i += 1
            continue

        # Ordinary HumanMessage, AIMessage, or SystemMessage.
        units.append([msg])
        i += 1

    def message_tokens(msg: BaseMessage) -> int:
        content = msg.content

        if not isinstance(content, str):
            content = str(content)

        if tokenizer is not None:
            try:
                return len(tokenizer(content))
            except Exception:
                pass

        # Avoid zero-token messages.
        return max(1, len(content) // 4)

    def unit_tokens(unit: List[BaseMessage]) -> int:
        return sum(message_tokens(msg) for msg in unit)

    # Work backward from the newest unit.
    selected: List[List[BaseMessage]] = []
    total = 0

    for unit in reversed(units):
        size = unit_tokens(unit)

        if total + size <= max_tokens:
            selected.append(unit)
            total += size
            continue

        # Do not stop entirely because one newest unit is too large.
        # Continue looking for smaller, older units that fit.
        continue

    selected.reverse()
    kept_rest = [msg for unit in selected for msg in unit]

    return kept_first + kept_rest



def tool_call_fingerprint(tool_name: str, args: dict) -> str:
    payload = {
        "tool": tool_name,
        "args": args,
    }

    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
    
def result_fingerprint(result: Any) -> str:
    encoded = canonical_json(result).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
    
def run_agent(
    user_request: str,
    max_iterations: int = 150,
    verbose: bool = False,
) -> str:
    execution_id = str(uuid.uuid4())
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]
    events: list[ToolEvent] = []
    iteration = 0
        
    recent_steps = deque(maxlen=12)
    step_counts = {}

    while iteration < max_iterations:
        iteration = iteration + 1
        if verbose:
            print(f"\n--- iteration {iteration + 1} ---")

        tool_calls = []
        response = {}
        for retry in range(10):
            try:
                response = llm_with_tools.invoke(messages)

                tool_calls = response.tool_calls or []
                content = response.content or ""

                if tool_calls or len(content.strip()) > 4:
                    break

                messages.append(
                    AIMessage(content=content)
                )
                messages.append(
                    HumanMessage(
                        content=(
                            "Your response was empty or unusable. "
                            "Return one valid tool call or content only."
                        )
                    )
                )

            except ResponseError as e:
                raw_content = str(e)

                print("ResponseError ", raw_content)
                events.append(
                    ToolEvent(
                        iteration=iteration + 1,
                        event_type="parse_error",
                        args={},
                        result={"error": str(e), "raw_output": raw_content},
                    )
                )

                messages.append(AIMessage(content=raw_content[:2000]))
                messages.append(
                    HumanMessage(
                        content=(
                            "The output above failed tool-call parsing.\n"
                            f"Error: {e}\n"
                            "Return exactly one valid tool call. "
                            "Do not explain your reasoning."
                        )
                    )
                )
                print("trying again")

        else:
            # Ten retries failed.
            print("Model failed to produce a valid response after 10 retries")
            

        messages.append(response)

        events.append(
            ToolEvent(
                iteration=iteration + 1,
                event_type="agent_response",
                args={},
                result=str(response)
            )
        )

        print("there are currently ",len(messages), " messages in the context")
        
        if verbose:
            if response.content:
                print("Assistant:", response.content[:2000])

        # The model is finished when it returns content and no tool calls.
        if len(tool_calls) == 0:
            if verbose:
                if response.content:
                    print("Assistant:", response.content)
            return {"condition" : "no tool calls",
                    "final_response": response.content,
                    "iterations": iteration + 1,
                    "events": events}

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call["id"]

            selected_tool = TOOLS_BY_NAME.get(tool_name)

            if selected_tool is None:
                tool_result = f"Unknown tool: {tool_name}"
                # 2. Don't count this as a real iteration
                iteration = iteration - 1
            else:
                try:
                    tool_result = selected_tool.invoke(tool_args)
                    # Ingest the tool result into evidence
                    
                    step_fingerprint = (
                        tool_call_fingerprint(tool_name, tool_args),
                        result_fingerprint(tool_result),
                    )

                    recent_steps.append(step_fingerprint)

                    step_counts[step_fingerprint] = step_counts.get(step_fingerprint, 0) + 1
                    
                    if step_counts[step_fingerprint] > 2:
                        tool_result = ({
                            "status": "stagnation_detected",
                            "message": (
                                "This tool call has been repeated and produced the same result. "
                                "Do not repeat it with the same arguments."
                            ),
                            "tool": tool_name,
                            "arguments": tool_args,
                            "repeated_count": step_counts[step_fingerprint],
                            "result" : tool_result,
                            "suggested_actions": [
                                "Use a different query or arguments",
                                "Use another tool",
                                "Apply the information already returned",
                                "Finish if the task is complete",
                            ],
                        })
                        print(tool_result)

                    
                except Exception as exc:
                    tool_result = (
                        f"Tool error: {type(exc).__name__}: {exc}"
                    )

            tool_result_event = ToolEvent(
                    iteration=iteration + 1,
                    event_type="tool_call_result",
                    tool=tool_name,
                    args=tool_args,
                    result=tool_result
                )
            events.append(tool_result_event)
            
            ingest_tool_event(execution_id, tool_result_event)

            if verbose:
                print(f"Executing: {tool_name}({str(tool_args)[:200]})")
                print(str(tool_result)[:200])
            else:
                print(f"Executing: {tool_name}()")

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )

        # Distillation now runs AFTER all tool results for this turn are in. Thanks Claude
        if response.usage_metadata.get("input_tokens", 0) > 20_000:
            print("Starting distill")
            conv_text = "\n".join(
                msg.content if isinstance(msg.content, str) else str(msg.content)
                for msg in messages
                if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))
            )
            distillation_messages = [
                SystemMessage(content=DISTILLATION_PROMPT),
                HumanMessage(content=conv_text),
            ]
            distilled = False
            facts_json = None
            for _ in range(3):
                try:
                    facts_json = distillation_llm.invoke(distillation_messages)
                    raw = facts_json.content.strip()
                    if raw.startswith("```"):
                        raw = raw.strip("`")
                        raw = raw[raw.find("{"):raw.rfind("}") + 1]
                    facts = json.loads(raw)
                    distilled = True
                    break
                except Exception as exc:
                    raw_content = facts_json.content if facts_json else "(no response)"
                    print(f"Distillation JSON parse failed: {exc}")
                    print(f"Raw model output (truncated): {raw_content[:300]}")

            if verbose:
                print("Distilled")
                print(facts_json)
            else:
                print("Distilled")


            if distilled:
                summary_msg = make_summary_message(facts)
                if len(messages) > 2 and is_summary_message(messages[2]):
                    messages = messages[:2] + [summary_msg] + messages[3:]
                else:
                    messages = messages[:2] + [summary_msg] + messages[2:]

                messages = truncate_history(messages, max_tokens=15_000, preserve=3)


    return {"condition" : f"Agent stopped after {max_iterations} iterations. The workspace may contain partial results.",
            "final_response": response.content,
            "iterations": iteration + 1,
            "events": events}



# ... all your existing code: SYSTEM_PROMPT, ToolEvent, tool functions,
# TOOLS_BY_NAME, run_agent() — unchanged, stays above this ...

from fastapi import FastAPI

app = FastAPI()

class AgentRequest(BaseModel):
    request: str
    max_iterations: int = 150
    verbose: bool = False

@app.post("/run")
def run(req: AgentRequest):
    result = run_agent(
        user_request=req.request,
        max_iterations=req.max_iterations,
        verbose=req.verbose,
    )
    return result

@app.get("/health")
def health():
    return {"status": "ok"}

