import os
import requests
import json
from typing import List, Dict, Any

def search_evidence_function(purpose: str, query: str, limit: int = 8, instance_number: int | None = None, execution_id: str  | None = None) -> str:
    """Search for specific information within large texts already retrieved in previous turns.

    CRITICAL: Use this tool INSTEAD of re-reading a file or re-fetching a URL if the content 
    was already retrieved once. Reading a full file again is inefficient and wasteful. 

    This is the mandatory next step after using web_fetch or read_file to isolate 
    relevant sections of a large document without reloading the entire source.

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
    execution_id: str, optional:
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
        
def compress_search_evidence(result: Any, limit: int) -> str:
    """Return the number of evidence chunks and a preview of the first."""
    
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
