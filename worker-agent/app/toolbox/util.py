from pathlib import Path
from typing import Any
import os

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache",  ".venv", "venv", ".mypy_cache", ".ruff_cache", ".npm", "node_modules"}

WORKSPACE_PATH = os.getenv(
    "WORKSPACE",
    "/srv/agent-workspaces",
)
WORKSPACE = Path(WORKSPACE_PATH)

WORKSPACE.mkdir(parents=True, exist_ok=True)

WORKSPACE = WORKSPACE.resolve()
print(WORKSPACE)

def middle_slice(text: str, limit: int) -> str:
    """Return a centered substring of `text` up to `limit` characters.

    Parameters
    ----------
    text : str
        Source string.
    limit : int
        Desired length (non‑negative).

    Returns
    -------
    str
        Substring of length <= `limit`.
    """
    if limit < 0:
        raise ValueError("limit must be non‑negative")

    n = len(text)
    if limit >= n:
        return text

    mid = n // 2                     # centre of the string (left of middle if even)
    half = limit // 2

    # start index – try to center the slice
    start = mid - half
    # for odd limits we need one extra char on the right side
    if limit % 2:
        # if we went too far left, push the slice right
        if start < 0:
            start = 0
    else:
        # for even limits the slice should be symmetrical
        if start < 0:
            start = 0

    # ensure we don't overshoot the end of the string
    if start + limit > n:
        start = n - limit

    return text[start:start + limit]


def clip_mid(value: Any, limit: int) -> str:
    """Return a clipped representation of ``value``.

    The function keeps the first 70 % of the string as a *head* and the
    last 30 % as a *tail*.  The omitted middle portion is indicated with a
    ``...[N chars omitted]...`` marker.

    If the input is not a string, it is converted to a string first.
    If the string length is already within ``limit``, it is returned
    unchanged.

    Parameters
    ----------
    value : Any
        The value to clip. Non‑string values are converted to ``str``.
    limit : int
        Maximum total length of the output string.

    Returns
    -------
    str
        The clipped string with the omitted portion marked.
    """
    s = value if isinstance(value, str) else str(value)
    if len(s) <= limit:
        return s
    head = int(limit * 0.7)
    tail = max(1, limit - head)
    omitted = len(s) - limit
    return f"{s[:head]}...[{omitted} chars omitted]...{s[-tail:]}"
    

def safe_path(relative_path: str) -> Path:
    """
    Resolve a relative path inside WORKSPACE, preventing escapes.
    """
    path = (WORKSPACE / relative_path).resolve()

    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"Path escapes workspace: {relative_path}")

    return path

