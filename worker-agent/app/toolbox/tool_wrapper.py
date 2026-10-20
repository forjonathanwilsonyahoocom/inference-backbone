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
        
    
    def get_repurpose(self):
        @tool
        def repurpose(instance_number: int, new_purpose: str):
            """Update the purpose of a previous tool call to refocus the semantic compressor

            This tool is intended to be called after one of
            "read_file", "web_fetch", "run_in_workspace"
            has already been executed. use the instance_number stamped on the tool result
            to rewrite the stored purpose to `new_purpose` 

            Parameters
            ----------
            instance_number: int
                The `instance_number` from the compressed tool result to refocus semantic compression.
            new_purpose: str
                The new purpose string to use for the semantic compression

            Returns
            -------
            str
                Confirmation message.
            """
            
            return repurpose_function(self.iterations, instance_number, new_purpose)
            
    def get_search_evidence(self):
        @tool
        def search_evidence(purpose: str, query: str, limit: int = 3, instance_number: int | None = None) -> str:
            """
            Search for specific information within large texts already retrieved in previous turns. CRITICAL: Use this tool INSTEAD of re-reading a file or re-fetching a URL if the content was already retrieved once. Reading a full file again is inefficient and wasteful. This is the mandatory next step after using web_fetch or read_file to isolate relevant sections of a large document without reloading the entire source.

            Parameters
            ----------
            purpose: str
                The specific piece of information you are looking for.
            query: str
                Search query string focused on the target information.
            limit: int, optional
                Max number of results to return.
            instance_number: int, optional
                Filter by instance number to narrow search to a specific previous iteration.
                
            Returns
            -------
            string representation of List[Dict]
                A list of the most relevant ranked chunks. Each chunk includes an 
                instance_number; use this as a filter to refine 
                your search within a specific turn.
            """
            return search_evidence_function(purpose, query, limit, instance_number, self.config.execution_id)
                




