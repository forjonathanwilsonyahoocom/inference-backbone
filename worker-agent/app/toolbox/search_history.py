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
        def search_history(about: str, query: str, limit: int = 3, instance_number: int | None = None) -> str:
            """Search current thread history for tool result fragments, use when history compaction obscures information.

Parameters
----------
about : str
    A short description of what the call is about, hint for summarization and retrieval.
query : str
    The search query string.
limit : int, optional
    Maximum number of chunks to return. Defaults to 3.
instance_number : int | None, optional
    Restrict to a specific iteration.

Returns
-------
str
    JSON‑encoded list of ranked evidence chunks. Empty list if none.
"""
            return search_history_function(about, query, limit, self.config.execution_id, instance_number)
        return search_history
                


def search_history_function(about: str, query: str, limit: int, execution_id: str, instance_number: int | None) -> str:
    """Internal helper for :func:`SearchHistoryWrapper.get_search_history`.

    Parameters
    ----------
    about : str
        A short, focused hint that guides the query.
    query : str
        The search query string.
    limit : int
        Maximum number of chunks to return.
    execution_id : str
        The current execution ID supplied by the framework.
    instance_number : int | None
        Optional filter to a specific iteration.

    Returns
    -------
    str
        JSON‑encoded list of ranked evidence chunks.
    """
    payload = {
        "query": query,
        "limit": limit,
    }
    if instance_number is not None:
        payload["instance_number"] = instance_number
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
    if len(parsed) == 0:
        return str(result)
    allowed_per = limit // len(parsed)
    return_list = []
    for hit in parsed:
        try:
            compressed_hit = {"properties": {"instance_number": hit["properties"]["instance_number"]}, "distance": hit["distance"]}
            compressed_line = hit["properties"]["content"]
            if len(compressed_line) > allowed_per:
                compressed_line = compressed_line[:allowed_per] + f"...[truncated {len(compressed_line) - allowed_per} chars]"
            compressed_hit["properties"]["content"] = compressed_line
            return_list.append(compressed_hit)
        except Exception as e:
            print(e)
            print(hit)
            return result
    return json.dumps(return_list, ensure_ascii=False, indent=2)
