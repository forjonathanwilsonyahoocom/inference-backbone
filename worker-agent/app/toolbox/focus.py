from langchain.tools import tool
from typing import List, Dict, Optional
from agent.models import Iteration, AgentRequest
import json


class FocusWrapper:
    """
    * Holds the list of Iterations
    * holds the config AgentRequest
    * provides @tool annotations that call functions that require access to local run state
    """
    def __init__(self, config: AgentRequest, iterations:  Optional[List[Iteration]] = None):
        self.iterations: List[Iteration] = iterations or []
        self.config: AgentRequest = config
        
    
    def get_focus(self):
        @tool
        def focus(instance_number: int, better_focus: str):
            """Update a tool result in history to refocus the chunk compressor query

            This tool is intended to be called after one of
            "read_file", "web_fetch", "run_in_workspace"
            has already been executed. use the instance_number stamped on the tool result
            to update chunk query to better_focus

            Parameters
            ----------
            instance_number:
                The `instance_number` from the compressed tool result to refocus semantic compression.
            better_focus:
                The new focus query for chunked compression

            Returns
            -------
                Confirmation message.
            """
            
            return focus_function(self.iterations, instance_number, better_focus)
        return repurpose
            


def focus_function(iterations: List[Iteration], instance_number: int, better_focus: str) -> str:
    """
    same as for @tool with the addition of
    new_purpose: str
        The new purpose string to inject.

    Returns
    -------
    str
        Confirmation message.
    """

    target: Iteration | None = None
    for it in iterations:
        if getattr(it, "tool_call_result_instance_number", None) == instance_number:
            target = it
            break
            
    if target is None:
        return f"No iteration with instance_number {instance_number} found."

    if target.model_response and target.model_response.tool_calls:
        target.tool_call_result_chunk_query = better_focus
    else:
        print(f"Iteration {instance_number} has no tool call to update.")
        return f"Iteration {instance_number} has no tool call to update."

    target.compression_limit = None
    target.tool_call_result_chunks = None
    
    return f"Updated purpose of iteration {instance_number} to '{new_purpose}'."
