
from langchain_core.tools import tool
from ddgs import DDGS
import json

@tool
def web_search(query: str) -> str:
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
            return f"Search completed, but no results were found for: '{clean_query}'"

        structured_results = []
        for item in raw_results:
            structured_results.append({
                "title": item.get("title", "No Title"),
                "url": item.get("href", ""),
                "snippet": item.get("body", "No description available.")
            })

        return json.dumps({"results": structured_results}, indent=2)

    except Exception as e:
        return f"Error: The DuckDuckGo search operation failed: {str(e)}"





