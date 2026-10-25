from fastapi import HTTPException
from pathlib import Path
import os
WORKSPACE_ROOT = Path(os.environ["WORKSPACE_ROOT"]).resolve()

def resolve_workspace(workspace: str) -> Path:
    # In a real service, look up authorization and workspace ownership here.
    # the caller supplies a path relative to the workspace never a host path.
    path = (WORKSPACE_ROOT / workspace).resolve()

    if not path.is_relative_to(WORKSPACE_ROOT) or not path.is_dir():
        raise HTTPException(status_code=404, detail="Workspace not found")

    return path


