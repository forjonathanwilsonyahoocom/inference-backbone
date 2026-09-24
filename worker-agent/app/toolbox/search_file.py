import json
from langchain_core.tools import tool

from toolbox.util import safe_path, WORKSPACE
from pathlib import Path

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

