from langchain_core.tools import tool
import os
import requests
import json
from toolbox.util import safe_path, clip_mid
from contracts.general_contracts.docker_broker import RunRequest, RunResponse
from typing import List, Dict, Any

@tool
def run_in_workspace(
    about: str,
    runtime: str,
    command: list[str],
    cwd: str,
    timeout_seconds: int = 300,
) -> str:
    """
    Run a command in the workspace using a specified runtime.

    Parameters
    ----------
    about : str
        A short description of what the call is about, hint for summarization and retrieval.
    runtime : str
        Supported runtimes: python, node, go, rust, php.
    command : list[str]
        The command and its arguments.
    cwd : str
        Working directory relative to the workspace root.
    timeout_seconds : int, optional
        Maximum execution time in seconds (default 300).

    Returns
    -------
    str
        JSON-encoded response from the docker-broker API.
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
    """Parse a previous ``run_in_workspace`` result, clip its logs to ``limit``
    characters, and return the JSON representation.

    If the input cannot be parsed as a ``RunResponse`` JSON object, the raw
    input is returned unchanged.

    Parameters
    ----------
    result : Any
        The JSON string returned by ``run_in_workspace``.
    limit : int
        Maximum number of characters to keep in the ``logs`` field.

    Returns
    -------
    str
        The clipped JSON representation of the response.
    """
    
    try:
        parsed = RunResponse.model_validate(json.loads(result))
    except Exception as e:
        print(f"failed to compress_run_in_workspace with {e} while parsing json {result} ")
        return result
                
    parsed.logs=clip_mid(parsed.logs, limit)
    
    return parsed.model_dump_json(indent=2)
