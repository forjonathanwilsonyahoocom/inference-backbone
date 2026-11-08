import os
import requests
import json

from langchain.tools import tool
from typing import List, Optional, Any
from contracts.inference_contracts.worker_agent_request import AgentRequest
import json



@tool
def search_info(about: str, query: str, limit: int, info_type_filter: Optional[str], execution_id_filter: Optional[str], instance_number_filter: Optional[int]) -> str:
    """
Search knowledge base for tool result fragments to propose linkages to

Parameters
----------
about : str
    A short description of what the call is about, hint for summarization and retrieval.
query : str
    The search query string.
limit : int
    Maximum number of chunks to return.
info_type_filter : Optional[str]
    optional filter for chunk source, type filters available:
    {"FinalAnswer",
     "Task",
     "AgentState.artifacts",
     "AgentState.observations",
     "AgentState.understandings",
     "AgentState.hypotheses",
     "AgentState.completed_steps",
     "AgentStateDelta.observations",
     "AgentStateDelta.understandings",
     "AgentStateDelta.hypotheses",
     "AgentStateDelta.completed_steps",
     "AgentStateDelta.artifacts,
     "Episode.mission",
     "Episode.significant_events",
     "Episode.findings",
     "Episode.lessons",
     "Episode.unresolved_questions",
     "Episode.evidence_refs"}
execution_id_filter : Optional[str]
    optional filter for chunk source (uuid4)
instance_number_filter : int
    optional filter for chunk source

Returns
-------
str
    JSON‑encoded list of ranked info chunks. Empty list if none.
    
"""
    payload = {
        "query": query,
        "limit": limit,
    }
    if instance_number_filter is not None and instance_number_filter > 0:
        payload["instance_number"] = instance_number_filter
    if execution_id_filter is not None and len(execution_id_filter) > 0:
        payload["execution_id"] = execution_id_filter
    if info_type_filter is not None and len(info_type_filter) > 0:
        payload["info_type"] = info_type_filter
    try:
        resp = requests.post("http://backbone-api:8000/search/info", json=payload, timeout=10)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps([{"error": str(e)}], ensure_ascii=False, indent=2)
        

def compress_search_info(result: Any, limit: int) -> str:
    """Return compressed evidence chunks."""
    try:
        parsed = json.loads(result)
    except Exception as e:
        print(f"failed to with {e} while parsing json {result} ")
        return result
    if not isinstance(parsed, list):
        print(f"compress_search_info fails on {result}")
        return result
    if len(parsed) == 0:
        return str(result)
    allowed_per = limit // len(parsed)
    return_list = []
    for hit in parsed:
        try:
            compressed_hit = {"properties": {"execution_id": hit["properties"]["execution_id"],
                                             "info_type": hit["properties"]["info_type"],
                                             "instance_number": hit["properties"]["instance_number"],
                                             "source_id": hit["properties"]["source_id"],
                                             }, 
                              "distance": hit["distance"]}
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
