from langchain_core.tools import tool
from typing import Any
import requests
import json

@tool
def web_fetch(about: str, url: str) -> str:
    """Fetches a URL and returns rendered markdown. stops at 5 redirects, no authentication

Parameters
----------
about : str
    A short description of what the call is about, hint for summarization and retrieval.
url : str
    Absolute URL to fetch.

Returns
-------
str
    JSON string: on success {"content": "<markdown>"}; on error [{"error": "<msg>"}].
"""
    payload = {"url" : url}
    try:
        resp = requests.post("http://web-tools:8000/fetch", json=payload, timeout=10)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False, indent=2)
        
    except Exception as e:
        return f"Error: Web fetch exception encountered during execution: {str(e)}"
        

#this expects the response from the web-tools api
def compress_web_fetch(result: Any, limit: int) -> str:
    """Return a preview of fetched content.

    We intentionally keep the original function untouched; this compressor
    simply truncates the content to a manageable size.
    """

    try:
        parsed = json.loads(result)
    except Exception as e:
        print(f"failed to with {e} while parsing json {result} ")
        return result
        
    if not isinstance(parsed, dict):
        print(f"compress_search_evidence fails on {result}")
        return result
        
    compressed_line = parsed["content"]
        
    if len(compressed_line) > limit:
        compressed_line = compressed_line[:limit] + f"...[truncated {len(compressed_line)  - limit} chars]"

    parsed["content"] = compressed_line
        
    return json.dumps(parsed, ensure_ascii=False, indent=2)



