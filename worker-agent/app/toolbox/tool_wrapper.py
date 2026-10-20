from langchain.tools import tool
from typing import List, Dict, Optional
from agent.models import Iteration, AgentRequest
from toolbox.repurpose import repurpose_function
from toolbox.search_evidence import search_evidence_function
import json


class ToolWrapper:
    """
    * Holds the list of Iterations
    * holds the config AgentRequest
    * provides @tool annotations that call functions that require access to local run state
    """
    def __init__(self, config: AgentRequest, iterations:  Optional[List[Iteration]] = None):
        self.iterations: List[Iteration] = iterations or []
        self.config: AgentRequest = config
        
    
    @tool(parse_docstring=True)
    def repurpose(self, instance_number: int, new_purpose: str):
        """Update the purpose of a previous tool call to refocus the semantic compressor

        This tool is intended to be called after one of
        "read_file", "web_fetch", "run_in_workspace"
        has already been executed. use the instance_number stamped on the tool result
        to rewrite the stored purpose to `new_purpose` 

        Args:
            instance_number: The `instance_number` from the first line of the target tool result
            new_purpose: The new purpose string to use for refocusing the semantic compression

        Returns:
            Confirmation that the target semantic compression is refocused
        """
        
        return repurpose_function(self.iterations, instance_number, new_purpose)
        
    @tool(parse_docstring=True)
    def search_evidence(self, purpose: str, query: str, limit: int = 3, instance_number: int | None = None) -> str:
        """
        Search for specific information within large texts already retrieved in previous turns.

        CRITICAL: Use this tool INSTEAD of re-reading a file or re-fetching a URL if the content 
        was already retrieved once. Reading a full file again is inefficient and wasteful. 

        This is the mandatory next step after using web_fetch or read_file to isolate 
        relevant sections of a large document without reloading the entire source.

        Args:
            purpose: the reason you are performing this search, used for future summary.
            query: Search query string focused on the target information.
            limit: Max number of results to return, default 3.
            instance_number: optional Filter by instance_number to focus on a specific instance.
            
        Returns:
            A list of the most relevant ranked chunks. Each chunk includes source instance_number
        """
        return search_evidence_function(purpose, query, limit, instance_number, self.config.execution_id)
            




