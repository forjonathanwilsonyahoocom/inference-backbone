
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

# ---------------------------------------------------------------------------
# Compressor implementations
# ---------------------------------------------------------------------------

def compress_read_file(result: Any) -> Dict[str, Any]:
    """Return a small summary of a file read.

    Parameters
    ----------
    result: str
        The full file content.

    Returns
    -------
    dict
        ``{"path": <path>, "size": <bytes>, "preview": <first 200 chars>}``
    """
    if not isinstance(result, str):
        return result
    size = len(result.encode("utf-8"))
    preview = result[:200]
    return {"size": size, "preview": preview}


def compress_write_file(result: Any) -> Dict[str, Any]:
    """Return a minimal representation of a write operation.

    Parameters
    ----------
    result: str
        The path written to.
    """
    return {"path": result}


def compress_edit_file(result: Any) -> Dict[str, Any]:
    """Return a minimal representation of an edit operation.

    Parameters
    ----------
    result: str
        The path edited.
    """
    return {"path": result}


def compress_run_command(result: Any) -> Dict[str, Any]:
    """Return a truncated stdout/stderr and exit code.

    Parameters
    ----------
    result: dict
        Expected to contain ``stdout``, ``stderr`` and ``exit_code``.
    """
    if not isinstance(result, dict):
        return result
    return {
        "exit_code": result.get("exit_code"),
        "stdout": result.get("stdout", "")[:200],
        "stderr": result.get("stderr", "")[:200],
    }


def compress_search_file(result: Any) -> Dict[str, Any]:
    """Return the number of hits and a preview of the first hit."""
    if not isinstance(result, list):
        return result
    return {"hits": len(result), "preview": result[0] if result else None}


def compress_search_evidence(result: Any) -> Dict[str, Any]:
    """Return the number of evidence chunks and a preview of the first."""
    if not isinstance(result, list):
        return result
    return {"hits": len(result), "preview": result[0] if result else None}


def compress_web_search(result: Any) -> Dict[str, Any]:
    """Return the top results and a preview of the first."""
    if not isinstance(result, list):
        return result
    return {"hits": len(result), "preview": result[0] if result else None}


def compress_web_fetch(result: Any) -> Dict[str, Any]:
    """Return a preview of fetched content.

    We intentionally keep the original function untouched; this compressor
    simply truncates the content to a manageable size.
    """
    if not isinstance(result, str):
        return result
    return {"preview": result[:200]}

# Mapping from tool name to compressor callable
COMPRESSORS: Dict[str, Callable[[Any], Any]] = {
    "read_file": compress_read_file,
    "write_file": compress_write_file,
    "edit_file": compress_edit_file,
    "run_command": compress_run_command,
    "search_file": compress_search_file,
    "search_evidence": compress_search_evidence,
    "web_search": compress_web_search,
    "web_fetch": compress_web_fetch,
}

# Helper to get a compressor or identity



def get_compressor(tool_name: str) -> Callable[[Any], Any]:
    return COMPRESSORS.get(tool_name, lambda x: x)

"""
possible use:

from toolbox.compressors import get_compressor

                    # compress the result before further processing
                    compressor = get_compressor(tool_name)
                    compressed_result = compressor(tool_result)
                    tool_result = compressed_result
                    # Ingest the tool result into evidence
                    


"""





"""End of compressors.py"""



