from typing import Any, List, Dict
from ddgs import DDGS
import json

async def web_search(query: str) -> List[Dict]:
    """Executes a keyword search on the live internet via DuckDuckGo.
    Use this first to find relevant URLs and snippets when asked about
    current events, weather, news, or fresh updates.

    Args:
        query: A standard web search keyword query.
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

