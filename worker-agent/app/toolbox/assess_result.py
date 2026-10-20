from langchain.tools import tool
from typing import List, Dict, Optional
from agent.models import Iteration, AgentRequest
import json


class AssessResultWrapper:
    """
    * Holds the list of Iterations
    * holds the config AgentRequest
    * provides @tool annotations that call functions that require access to local run state
    """
    def __init__(self, config: AgentRequest, iterations:  Optional[List[Iteration]] = None):
        self.iterations: List[Iteration] = iterations or []
        self.config: AgentRequest = config
        
    
    def get_assess_result(self):
        @tool
        def assess_result(instance_number: int, utility: float, better_focus: Optional[str] = None):
            """Use to update a tool result in history to assess its utility in the current thread and refocus the chunk compressor query

            This tool is intended to be called after one of
            "read_file", "web_fetch", "run_in_workspace"
            has already been executed. use the instance_number stamped on the tool result
            to update chunk query to better_focus and 

            Parameters
            ----------
            instance_number:
                The `instance_number` from the compressed tool result to refocus semantic compression.
            utility: 
                measures how much the result actually helps achieve your objective
            better_focus:
                The new focus query for chunked compression

            Returns
            -------
                Confirmation message.
            """
            
            return assess_result_function(self.iterations, instance_number, relevance, better_focus)
        return assess_result
            


def assess_result_function(iterations: List[Iteration], instance_number: int, utility: float, better_focus: str | None) -> str:
    """
    same as for @tool with the addition of
    iterations: List[Iteration]
        the current execution history.

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

    if  better_focus is not None:
        if target.model_response and target.model_response.tool_calls:
            target.tool_call_result_chunk_query = better_focus
        else:
            print(f"Iteration {instance_number} has no tool call to update.")
            return f"Iteration {instance_number} has no tool call to update."

        target.compression_limit = None
        target.tool_call_result_chunks = None
        
    if utility != target.tool_call_result_utility:
        target.tool_call_result_utility = utility
        target.compression_limit = None        
        
    return f"Updated assessment of result instance_number {instance_number} utility {utility} with focus: '{better_focus | target.tool_call_result_chunk_query } '."
