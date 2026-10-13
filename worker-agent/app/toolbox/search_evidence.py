from langchain_core.tools import tool
import os
import requests
import json
from typing import List, Dict, Any

@tool
def search_evidence(purpose: str, query: str, limit: int = 8, instance_number: int | None = None, execution_id: str  | None = None) -> str:
    """
    Search text already fetched or read in this execution.

    Use this tool instead of calling `web_fetch`, `read_file`, or another
    large-output tool again when you need to find, recall, or verify details
    from content that was already returned in a previous iteration. Previously
    read content may have been compressed; this tool searches its stored chunks
    by meaning and returns the best matches.

    Call this tool after fetching or reading a large document, and whenever a
    later step needs information from that document. Do not reread or refetch
    the document just to locate a passage or recover a detail.

    Parameters
    ----------
    purpose: str
        The immediate purpose of this search.
    query: str
        What information to find in the previously read content.
    limit: int, optional
        Maximum number of matching chunks to return.
    instance_number: int, optional
        Restrict the search to a specific iteration. Use an instance_number
        from a prior result to focus on that iteration.
    execution_id: str, optional
        Overridden by the framework with the current execution_id.

    Returns
    -------
    string
        A representation of a ranked list of matching chunks. Each chunk
        includes its instance_number, which can be used to narrow later searches.
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
