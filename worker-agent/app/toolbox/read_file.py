
from langchain_core.tools import tool

from toolbox.util import safe_path
from typing import Optional

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


