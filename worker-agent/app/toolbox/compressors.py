
# compressors.py
"""Utility functions to compress tool outputs before sending back to the LLM.

Each tool namespace can provide a custom compressor that reduces the size of the
payload while preserving the essential information needed for downstream
processing.  The compressor is a simple callable that accepts the raw tool
result and returns a lightweight representation.

The mapping is intentionally minimal – only the tools that are known to produce
large payloads are included.  If a tool is not in the mapping, its output is
returned unchanged.
"""

from typing import Any, Callable, Dict
from toolbox.run_command import compress_run_command
from toolbox.search_file import compress_search_file
from toolbox.search_evidence import compress_search_evidence
from toolbox.web_search import compress_web_search
from toolbox.web_fetch import compress_web_fetch

# ---------------------------------------------------------------------------
# Compressor implementations
# ---------------------------------------------------------------------------

def compress_read_file(result: Any, limit: int) -> str:
    """Return a small summary of a file read.

    Parameters
    ----------
    result: str
        The current content.

    Returns
    -------
    str
        truncated to limit with markers
    """
    result = str(result)
    
    size = len(result.encode("utf-8"))
    
    if size > limit:
        return result[:limit] + f"\n...[truncated {size - limit} chars]"
    
    return result




# Mapping from tool name to compressor callable
COMPRESSORS: Dict[str, Callable[[Any, int], Any]] = {
    "read_file": compress_read_file,
    "run_command": compress_run_command,
    "search_file": compress_search_file,
    "search_evidence": compress_search_evidence,
    "web_search": compress_web_search,
    "web_fetch": compress_web_fetch,
}

# Helper to get a compressor or identity

def get_compressor(tool_name: str) -> Callable[[Any], Any]:
    return COMPRESSORS.get(tool_name, lambda x, y: x)

"""End of compressors.py"""



