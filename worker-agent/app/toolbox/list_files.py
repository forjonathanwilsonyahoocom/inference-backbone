from toolbox.util import safe_path, WORKSPACE, EXCLUDED_DIRS
from langchain_core.tools import tool

@tool
def list_files(
    purpose: str, 
    path: str = ".",
    glob_filter_to: str = "*",
    exclude: set[str] | None = None,
    limit: int = 300,
) -> str:
    """List files and directories in the current project workspace.

The tool accepts a glob pattern and an optional set of directories to exclude.
It returns a JSON‑encoded string containing the first ``limit`` entries.

Parameters
----------
purpose : str
    The immediate purpose of this call.
path : str, optional
    The directory to list, relative to the workspace root. Defaults to ``"."``.
glob_filter_to : str, optional
    Glob pattern to filter the results. Defaults to ``"*"``.
exclude : set[str] | None, optional
    Directories to exclude from the listing.
limit : int, optional
    Maximum number of entries to return.

Returns
-------
str
    JSON‑encoded list of file paths.
"""
    exclude = EXCLUDED_DIRS | (exclude or set())
    target_path = safe_path(path)

    entries = []
    truncated = False

    for candidate in target_path.rglob(glob_filter_to):
        relative = candidate.relative_to(WORKSPACE)

        if any(part in exclude for part in relative.parts):
            continue

        if len(entries) == limit:
            truncated = True
            break

        suffix = "/" if candidate.is_dir() else ""
        entries.append(f"{relative}{suffix}")

    if truncated:
        entries.append(
            f"truncated: showing {limit} entries; more results exist. "
            "Use a narrower glob_filter_to or exclude directories by name."
        )

    return "\n".join(entries) if entries else "(workspace is empty)"
    
