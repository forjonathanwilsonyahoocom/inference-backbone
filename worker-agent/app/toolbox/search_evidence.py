from langchain_core.tools import tool
import os
import requests
import json
from typing import List, Dict, Any

@tool
def search_evidence(query: str, limit: int = 8, instance_number: int | None = None, execution_id: str  | None = None) -> str:
    """Search chunked content from previous iterations.
    use when previous iteration details have been compressed away
    
    this is an essential tool after using web_fetch 
    or any tool that returns large amounts of text that
    may be immediately removed from the context

    Parameters
    ----------
    query: str
        Search query string.
    limit: int, optional
        Max number of results to return.
    instance_number: int, optional
        Filter by instance number if provided.
    execution_id: str, optional:
        overridden by framework

    Returns
    -------
    string representation of List[Dict]
        List of ranked chunks from previous iterations.
        result chunks will include the instance_number, use the
        instance_number as a filter to focus on a single iteration
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
        return json.dumps(json.resp.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False, indent=2)
        
def compress_search_evidence(result: Any, limit: int) -> str:
    """Return the number of evidence chunks and a preview of the first."""
    
    parsed = json.loads(result)
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
