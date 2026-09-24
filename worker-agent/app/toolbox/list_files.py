from toolbox.util import safe_path, WORKSPACE, EXCLUDED_DIRS

from langchain_core.tools import tool

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
    
