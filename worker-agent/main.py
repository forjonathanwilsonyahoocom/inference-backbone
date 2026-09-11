import json
import os
import subprocess
from pathlib import Path
from typing import Any, overload, Mapping, List, Dict, Iterable, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass
from ollama import ResponseError 
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

MODEL_NAME = os.getenv(
    "OLLAMA_MODEL",
    "gpt-oss:20b",
)

llm = ChatOllama(
    model=MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    temperature=0.01,
    num_ctx=40960,
)
distillation_llm = ChatOllama(
    model=MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    temperature=0.01,
    num_predict=5000,  # distillation JSON should never need more than this
)
print(f"Using {MODEL_NAME} at {OLLAMA_BASE_URL}")


class ToolEvent(BaseModel):
    iteration: int
    event_type: str
    tool: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None

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
                    "--disable-dev-shm-usage",                      # Use disk swap to avoid shared memory engine crashes
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

    # Resolve path safely
    target_path = safe_path(path)

    # Basic existence check
    if not target_path.exists():
        return f"Path does not exist: {path}"

    # Helper to search a single file and return matches
    def _search_single(file: Path) -> List[Dict[str, str]]:
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

    if target_path.is_file():
        results.extend(_search_single(target_path))
    else:
        # Directory: iterate recursively over all files
        for file in target_path.rglob("*"):
            if file.is_file():
                results.extend(_search_single(file))
                # Optional: stop early if a global limit is desired

    return json.dumps(results, ensure_ascii=False, indent=2)






@tool
def list_files() -> str:
    """List files and directories in the current project workspace."""
    entries = []

    for path in sorted(WORKSPACE.rglob("*")):
        relative = path.relative_to(WORKSPACE)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
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

if the third message decribes a tool call, we are on the first distillation pass for this thread

use the information from the context to infer the progress of the thread and help form the direction of the tool enabled agent

output **only** a single JSON object with these top‑level keys:
  - artifacts:   [{ "id":"", "type":"", "value":"" }]
  - claims:      [{ "statement":"", "source":"", "confidence":0‑1 }]
  - understandings:[{ "concept":"", "detail":""}]
  - hypotheses:  [{ "hypothesis":"", "status":"pending/confirmed/ruled‑out", "confidence":0‑1 }]
  - direction:   [{ "step":"", "deadline":"YYYY‑MM‑DD"}]

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
   • Suggest metrics to capture (token‑rate, query latency, GPU utilisation) and how to log them.

5. **Ask Clarifying Questions When Needed**
   • If any environmental detail is missing (e.g., Docker version, data location, existing ontology files), ask for it.
   • Do not bombard with questions; one or two targeted ones per turn are enough.

6. **Use a Friendly, Future‑Oriented Tone**
   • Encourage experimentation, celebrate small wins, and keep the user motivated.
You are not allowed to declare success without reproducing and recording evidence..

Current World Model:
- Inspect existing files.
- Use write_file to create example implementaions.
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
     Return a *new* list that

    1. always keeps the first ``preserve`` messages (default 2),
    2. truncates the *remaining* messages so that the total token count
       (estimated or actual, depending on ``tokenizer``) does not exceed
       ``max_tokens``.

    The original message list is never mutated.

    Parameters
    ----------
    messages: List[BaseMessage]
        All messages in chronological order (index 0 is the oldest).
    max_tokens: int, default 25_000
        Token budget for the *truncated* part of the history.
        Tokens used by the preserved messages are *not* counted.
    tokenizer: callable, optional
        If supplied, must accept a string and return an object whose
        ``__len__`` gives the token count.  This is useful when you
        want an exact count rather than the 1‑token ≈ 4‑chars heuristic.
    preserve: int, default 2
        Number of messages that must stay in the returned list regardless
        of their size.

    Returns
    -------
    List[BaseMessage]
        A new list containing the preserved messages followed by the
        truncated remainder, but operates on *turns* instead of individual
        messages, so an AIMessage with tool_calls and its ToolMessage results
        are always kept or dropped together.
    """
    msg_len = len(messages)
    if msg_len <= preserve:
        return messages.copy()

    kept_first = messages[:preserve]
    rest = messages[preserve:]

    # Group `rest` into turns: a turn starts at a HumanMessage or an
    # AIMessage, and absorbs any immediately-following ToolMessages.
    turns: List[List[BaseMessage]] = []
    for msg in rest:
        if isinstance(msg, ToolMessage) and turns:
            turns[-1].append(msg)
        else:
            turns.append([msg])

    def turn_tokens(turn: List[BaseMessage]) -> int:
        total = 0
        for msg in turn:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            if tokenizer is not None:
                try:
                    total += len(tokenizer(content))
                    continue
                except Exception:
                    pass
            total += len(content) // 4
        return total

    total = 0
    kept_turns = []
    for turn in reversed(turns):
        n = turn_tokens(turn)
        if total + n > max_tokens:
            print("truncating")
            break
        kept_turns.append(turn)
        total += n

    kept_rest = [msg for turn in reversed(kept_turns) for msg in turn]
    return kept_first + kept_rest


def run_agent(
    user_request: str,
    max_iterations: int = 150,
    verbose: bool = False,
) -> str:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]
    events: list[ToolEvent] = []
    iteration = 0
    while iteration < max_iterations:
        iteration = iteration + 1
        if verbose:
            print(f"\n--- iteration {iteration + 1} ---")

        tool_calls = []
        response = {}
        try:
            for _ in range(3):
                response = llm_with_tools.invoke(messages)
                tool_calls = response.tool_calls or []
                content = response.content or ""
                #try this a few times if we get no tool calls AND no content
                if len(tool_calls) > 0 or len(content) > 4:
                    break
        except ResponseError as e:
            # 1. Show the error to the LLM
            print(f"Parsing response from LLM failed: {e}")
            
            events.append(
                ToolEvent(
                    iteration=iteration + 1,
                    event_type="parse_error",
                    args={},
                    result=str(e)
                )
            )
            messages.append(
                SystemMessage(
                    content=f"⚠️  Parsing error: {e}. "
                            "Generate a correct tool call or explain the issue."
                )
            )
            # 2. Don't count this as a real iteration
            iteration = iteration - 1
            continue


        messages.append(response)

        events.append(
            ToolEvent(
                iteration=iteration + 1,
                event_type="agent_response",
                args={},
                result=str(response)
            )
        )

        print(len(messages))
        
        if verbose:
            if response.content:
                print("Assistant:", response.content[:200])

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
            else:
                try:
                    tool_result = selected_tool.invoke(tool_args)
                except Exception as exc:
                    tool_result = (
                        f"Tool error: {type(exc).__name__}: {exc}"
                    )

            events.append(
                ToolEvent(
                    iteration=iteration + 1,
                    event_type="tool_call",
                    tool=tool_name,
                    args=tool_args,
                    result=tool_result
                )
            )

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
        if response.usage_metadata.get("input_tokens", 0) > 20000:
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

