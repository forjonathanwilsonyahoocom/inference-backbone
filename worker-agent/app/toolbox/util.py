from pathlib import Path
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


def safe_path(relative_path: str) -> Path:
    """
    Resolve a user-provided path inside WORKSPACE.
    Prevents paths such as ../../etc/passwd.
    """
    path = (WORKSPACE / relative_path).resolve()

    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError(f"Path escapes workspace: {relative_path}")

    return path

