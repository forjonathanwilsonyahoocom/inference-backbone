from langchain_core.tools import tool
from typing import Any
import requests
import json

@tool
def web_search(about: str, query: str) -> str:
    """Search the web via DuckDuckGo.

    Parameters
    ----------
    about : str
        A short description of what the call is about, hint for summarization and retrieval.
    query : str
        Search query string.

    Returns
    -------
    str
        JSON string of results: list of dicts with keys `title`, `href`, `body`,
        or an `error` key on failure.
    """
    clean_query = query.strip()
    if not clean_query:
        return "Error: The provided search query was empty."

    payload = {"query" : clean_query}
    
    try:
        resp = requests.post("http://web-tools:8000/search", json=payload, timeout=10)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False, indent=2)


def compress_web_search(result: Any, limit: int) -> str:
    """Return the top results with truncated previews."""
 
    try:
        parsed = json.loads(result)
    except Exception as e:
        print(f"failed to with {e} while parsing json {result} ")
        return result
        
    if not isinstance(parsed, list):
        print(f"compress_web_search fails on {result}")
        return result
    
    if len(parsed) == 0:
        return str(result)
        
    allowed_per = limit // len(parsed)
    
    return_list = []
    
    if not isinstance(result, list):
        return result

    for hit in parsed:       
        compressed_line = hit["body"]
        
        if len(compressed_line) > allowed_per:
            compressed_line = compressed_line[:allowed_per] + f"...[truncated {len(compressed_line)  - allowed_per} chars]"

        hit["body"] = compressed_line
        
        return_list.append(hit)
        
    return json.dumps(return_list, ensure_ascii=False, indent=2)




