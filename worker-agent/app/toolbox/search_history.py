import os
import requests
import json
from typing import List, Dict, Any

from langchain.tools import tool
from typing import List, Dict, Optional
from agent.models import AgentRequest, Iteration
import json


class SearchHistoryWrapper:
    """
    * holds the config AgentRequest
    * provides @tool curry interface from signature shown to llm to what function requires 
    """
    def __init__(self, config: AgentRequest, iterations:  Optional[List[Iteration]] = None):
        self.config: AgentRequest = config
        self.iterations:  List[Iteration] = iterations or []
        
    def get_search_history(self):
        @tool
        def search_history(purpose: str, query: str, limit: int = 3, instance_number: int | None = None) -> str:
            """
            Use to Search for specific information from previous turns. CRITICAL: Use this tool INSTEAD of re-reading a file or re-fetching a URL if the content is truncated during compression. Reading a full website again is inefficient and wasteful. This is the recommended next step after using web_fetch to isolate relevant sections of a large document without reloading the entire source.

            Parameters
            ----------
            purpose:
                focus hint when history is compacted
            query:
                Search query string focused on the target information.
            limit: 
                Max number of chunks to return.
            instance_number: 
                Filter by instance_number to narrow search to a specific previous iteration.
                If None, searches across all iterations.
                
            Returns
            -------
            str
                the most relevant ranked chunks. Each chunk includes an 
                instance_number; use this as a filter to refine 
                your search within a specific turn.

            Notes
            -----
            * If no matching chunks are found, an empty JSON array (`[]`) is returned.
            * The search is performed against the backbone-api evidence store.
            """
            return search_history_function(purpose, query, limit, self.config.execution_id, instance_number)
        return search_history
                

def search_history_function(purpose: str, query: str, limit: int, execution_id: str, instance_number: int | None) -> str:
    """
    Parameters
    ----------
    same as for @tool with the addition of:
    execution_id: str:
        Overridden by framework to current execution_id.

    Returns
    -------
    string representation of List[Dict]
        A list of the most relevant ranked chunks. Each chunk includes an 
        instance_number; use this as a filter in subsequent calls to refine 
        your search within a specific document version.
    """
    payload = {
        "query": query,
        "limit": limit,
    }
    if instance_number is not None:
        payload["instance_number"] = instance_number
    # default execution_id from env if set
    if execution_id:
        payload["execution_id"] = execution_id
    try:
        resp = requests.post("http://backbone-api:8000/search/evidence", json=payload, timeout=10)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False, indent=2)
        
def compress_search_history(result: Any, limit: int) -> str:
    """Return compressed evidence chunks."""
    
    try:
        parsed = json.loads(result)
    except Exception as e:
        print(f"failed to with {e} while parsing json {result} ")
        return result
        
    if not isinstance(parsed, list):
        print(f"compress_search_evidence fails on {result}")
        return result
    
    if  len(parsed) == 0:
        return str(result)
        
    allowed_per = limit // len(parsed)
    
    return_list = []
    
    for hit in parsed:
        try:
            #hit is a contracts.EvidenceChunk
            compressed_hit = {"properties" : {"instance_number" : hit["properties"]["instance_number"]}, "distance" : hit["distance"]}
            
            compressed_line = hit["properties"]["content"]
            
            if len(compressed_line) > allowed_per:
                compressed_line = compressed_line[:allowed_per] + f"...[truncated {len(compressed_line)  - allowed_per} chars]"
            compressed_hit["properties"]["content"] = compressed_line
            
            return_list.append(compressed_hit)
        except Exception as e:
            print(e)
            print(hit)
            return result
        
    return json.dumps(return_list, ensure_ascii=False, indent=2)
