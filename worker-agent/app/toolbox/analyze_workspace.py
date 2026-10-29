from langchain_core.tools import tool
import os
import requests
import json
from toolbox.util import safe_path, clip_mid
from contracts.general_contracts.docker_broker import RunRequest, RunResponse
from typing import List, Dict, Any

@tool
def analyze_workspace(
    about: str,
    with_tool: str,
    cwd: str,
    timeout_seconds: int = 300,
) -> str:
    """Use when inspecting an unexplored working directory for summary information
    Synchronously runs a specified outline digest tool in the workspace.

    Parameters
    ----------
    about : str
        A short description of what the call is about, hint for summarization and retrieval.
    with_tool : str
        Supported tools: 
            ast : (recursive abstract syntax tree outline).
            text : (recursive text natural language digest).
    cwd : str
        Working directory relative to the workspace root.
    timeout_seconds : int, optional
        Maximum execution time in seconds (default 300).

    Returns
    -------
    str
        JSON-encoded response from the docker broker.
    """
    #this fails with exception if path is not safe
    workspace_path = safe_path(cwd)
    
    if cwd.startswith("./"):
        cwd = cwd[2:]
    
    tool_commands = {"ast" :  ["outline", "./"], #NOTE to developer, the ./ here is relative to the specified cwd
                     "text" : ["--ext", "*.*"],
                    } 
                    
    command = tool_commands.get(with_tool, None)
    
    if command is None:
        raise Exception(f"the specified tool {with_tool} is not supported, try one of {tool_commands.keys()}")
    
    payload = RunRequest(workspace=cwd,
                         runtime=with_tool,
                         command=command,
                         timeout_seconds=timeout_seconds)
    
    try:
        resp = requests.post("http://docker-broker:8000/on_demand", json=payload.model_dump(), timeout=int(timeout_seconds * 1.2))
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
        
def compress_analyze_workspace(result: Any, limit: int) -> str:
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
