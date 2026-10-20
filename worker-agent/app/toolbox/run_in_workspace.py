from langchain_core.tools import tool
import os
import requests
import json
from toolbox.util import safe_path, clip_mid
from contracts.general_contracts.docker_broker import RunRequest, RunResponse
from typing import List, Dict, Any

@tool
def run_in_workspace(
    purpose: str,
    runtime: str,
    command: list[str],
    cwd: str,
    timeout_seconds: int = 300,
) -> str:
    """Run a command in the current workspace using an approved language runtime.

    Supported runtimes: python, node, go, rust, php. The command can read and modify workspace files
    from a brokered docker runtime, Returns the command output and exit status. Execution is
    subject to time and resource limits; do not use this tool for unrelated system administration.
    """
    #this fails with exception if path is not safe
    workspace_path = safe_path(cwd)
    
    if cwd.startswith("./"):
        cwd = cwd[2:]
        
    payload = RunRequest(workspace=cwd,
                         runtime=runtime,
                         command=command,
                         timeout_seconds=timeout_seconds)
    
    try:
        resp = requests.post("http://docker-broker:8000/jobs", json=payload.model_dump(), timeout=int(timeout_seconds * 1.2))
        resp.raise_for_status()
                
        parsed = RunResponse.model_validate(resp.json())
        parsed.logs=clip_mid(parsed.logs, 3000)
        
        return parsed.model_dump_json(indent=2)
        
    except Exception as e:
        print(f"failed to run_in_workspace with {e} while parsing json {resp.json()} ")
        error_return = RunResponse(exit_code=1,
                                   timed_out = False,
                                   logs = f"error: {str(e)}")
    
        
    
        return error_return.model_dump_json(indent=2)
        
def compress_run_in_workspace(result: Any, limit: int) -> str:
    """Return the number of evidence chunks and a preview of the first."""
    
    try:
        parsed = RunResponse.model_validate(json.loads(result))
    except Exception as e:
        print(f"failed to compress_run_in_workspace with {e} while parsing json {result} ")
        return result
                
    parsed.logs=clip_mid(parsed.logs, limit)
    
    return parsed.model_dump_json(indent=2)
