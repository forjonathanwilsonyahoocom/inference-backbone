from typing import Any, List, Dict
from ddgs import DDGS
import json

async def web_search(query: str) -> List[Dict]:
    """Executes a keyword search on DuckDuckGo.

Parameters
----------
query : str
    Search query string.

Returns
-------
List[Dict]
    List of result dictionaries with keys 'title', 'href', 'body'.
"""
    clean_query = query.strip()
    if not clean_query:
        return "Error: The provided search query was empty."

    try:
        # Initializing DuckDuckGo Search Client
        with DDGS() as ddgs:
            # Gather up to 4 clean results to reduce token clutter
            raw_results = list(ddgs.text(clean_query, max_results=4))

        if not raw_results:
            return [{"body" : f"Search completed, but no results were found for: '{clean_query}'"}]

        return raw_results

    except Exception as e:
        return [{"body" : f"Error: The DuckDuckGo search operation failed: {str(e)}"}]

