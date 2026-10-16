from toolbox.util import safe_path, WORKSPACE, EXCLUDED_DIRS
from langchain_core.tools import tool

@tool
def list_files(purpose: str, path: str = ".", glob_filter: str = "*") -> str:
    """List files and directories in the current project workspace.
    only returns the top 300 entries, filter to focus if required
    glob_filter docs: https://docs.python.org/3/library/glob.html#glob.glob
     """
    entries = []
    
    target_path = safe_path(path)
    filepaths = sorted(target_path.rglob(glob_filter))
    total_num_files = len(filepaths)
    limit = 300
    for path in filepaths[:limit]:
        relative = path.relative_to(WORKSPACE)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{relative}{suffix}")
    if total_num_files > limit:
        entries.append(f"truncated: showing {limit} of {total_num_files} entries, try a more restrictive glob_filter")
    return "\n".join(entries) if entries else "(workspace is empty)"
    
