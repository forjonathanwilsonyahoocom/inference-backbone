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
            """Search the backbone‑api evidence store for previously indexed chunks of tool results.

            The evidence store is automatically populated after each tool call: the raw
            result is split into chunks, each chunk is sent to the vector store, and the
            chunk is tagged with an ``instance_number`` that identifies the iteration in
            which it was produced.  This tool is the **preferred way to recall
            information from earlier turns** when the conversation has been compressed –
            re‑reading a file or re‑fetching a URL is inefficient and wasteful.

            Parameters
            ----------
            purpose : str
                A short, focused hint that guides the query.  When the history has
                been compacted, this helps the vector store rank the most relevant
                chunks.
            query : str
                The search query string.  It should be focused on the specific
                information you are looking for.
            limit : int, optional
                Maximum number of chunks to return, ordered by distance (most
                relevant first).  Defaults to ``3``.
            instance_number : int | None, optional
                If supplied, restricts the search to chunks produced in the
                iteration whose AIMessage was stamped with this ``instance_number``.
                The AIMessage that issued the tool call carries the preceding
                ``instance_number`` – e.g. if the tool call was the 5th action,
                the AIMessage carries ``instance_number=5`` and the resulting tool
                result is stamped with ``instance_number=6``.  Use this to narrow a
                search to a specific turn.  If ``None``, the search spans all
                iterations.

            Returns
            -------
            str
                A JSON‑encoded list of ranked evidence chunks.  Each chunk
                includes an ``instance_number`` property and the original
                content (truncated if it exceeds ``limit // len`` to keep the
                response bounded).  If no matching chunks are found, an empty
                JSON array ``[]`` is returned.

            Notes
            -----
            * The search is performed against the backbone‑api evidence store at
              ``http://backbone-api:8000/search/evidence``.
            * The request times out after 10 seconds.
            * On error the response is a JSON array with an ``error`` key.
            * Use ``instance_number`` to filter to a specific iteration when you
              need to recall what happened in a particular turn.
            """
            return search_history_function(purpose, query, limit, self.config.execution_id, instance_number)
        return search_history
                


def search_history_function(purpose: str, query: str, limit: int, execution_id: str, instance_number: int | None) -> str:
    """Internal helper for :func:`SearchHistoryWrapper.get_search_history`.

    Parameters
    ----------
    purpose : str
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
