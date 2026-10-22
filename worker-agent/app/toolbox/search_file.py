import json
from langchain_core.tools import tool
from typing import Any
from toolbox.util import safe_path, WORKSPACE, EXCLUDED_DIRS
from pathlib import Path

from typing import List, Dict

def _is_binary(file: Path, sample_size: int = 1024) -> bool:
    try:
        with open(file, "rb") as f:
            return b"\x00" in f.read(sample_size)
    except Exception:
        return True

@tool
def search_file(about: str, path: str, query: str) -> str:
    """
Search for an exact text match in a file or directory.

Parameters
----------
about : str
    A short description of what the call is about, hint for summarization and retrieval.
path : str
    File or directory path relative to workspace.
query : str
    Exact text to find.

Returns
-------
str
    JSON array of matches: {"file":..., "line":..., "text":...}. Empty array if none. Error message if path missing.
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
                stripped = line.strip()
                matches.append({"file": str(file.relative_to(WORKSPACE)), "line": i, "text": stripped})
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




def compress_search_file(result: Any, limit: int) -> str:
    """retains the lines with hits but reduces size"""
 
    try:
        parsed = json.loads(result)
    except Exception as e:
        print(f"failed to with {e} while parsing json {result} ")
        return result
        
    if not isinstance(parsed, list):
        print(f"compress_search_file fails on {result}")
        return result
        
    if len(parsed) == 0:
        return str(result)
        
    allowed_per = limit // len(parsed)
    
    return_list = []
    
    for hit in parsed:
        compressed_line = hit["text"]
        if len(compressed_line) > allowed_per:
            compressed_line = compressed_line[:allowed_per] + f"...[truncated {len(compressed_line)  - allowed_per} chars]"
        
        return_list.append({"file": hit["file"], "line": hit["line"], "text": compressed_line})
        
    return json.dumps(return_list, ensure_ascii=False, indent=2)

