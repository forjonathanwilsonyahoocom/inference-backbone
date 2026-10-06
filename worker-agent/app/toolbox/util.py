from pathlib import Path
from typing import Any
import os

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv", ".mypy_cache", ".ruff_cache"}

WORKSPACE_PATH = os.getenv(
    "WORKSPACE",
    "/agentworkspace",
)
WORKSPACE = Path(WORKSPACE_PATH)

WORKSPACE.mkdir(parents=True, exist_ok=True)

WORKSPACE = WORKSPACE.resolve()
print(WORKSPACE)



def clip_mid(value: Any, limit: int) -> str:
    """Return a clipped representation of ``value``.

    The function keeps the first 70 % of the string as a *head* and the
    remainder as a *tail*.  The omitted portion is indicated with a
    ``...[N chars omitted]...`` marker.
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
    Resolve a user-provided path inside WORKSPACE.
    Prevents paths such as ../../etc/passwd.
    """
    path = (WORKSPACE / relative_path).resolve()

    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"Path escapes workspace: {relative_path}")

    return path

