from langchain_core.tools import tool
import os
import requests
from typing import List, Dict

@tool
def search_evidence(query: str, limit: int = 8, instance_number: int | None = None) -> List[Dict]:
    """Search chunked content from previous iterations.
    use when previous iteration details have been compressed away

    Parameters
    ----------
    query: str
        Search query string.
    limit: int, optional
        Max number of results to return.
    instance_number: int, optional
        Filter by instance number if provided.

    Returns
    -------
    List[Dict]
        List of chunks from previous iterations.
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
    exec_id = os.getenv("CURRENT_EXECUTION_ID")
    if exec_id:
        payload["execution_id"] = exec_id
    try:
        resp = requests.post("http://backbone-api:8000/search/evidence", json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return [{"error": str(e)}]
