from typing import Any, List
from agent.models import Iteration


def repurpose_function(iterations: List[Iteration], instance_number: int, new_purpose: str) -> str:
    """Update the purpose of a previous tool call.

    This tool is intended to be called after one of the unstructured tools
    which are listed in tool wrapper     has already been executed.  It finds the iteration whose
    ``tool_call_result_instance_number`` matches ``instance_number`` and
    rewrites the stored ``tool_calls[0].args['purpose']`` to
    ``new_purpose``.  It also clears the compression state so that the
    next compression pass will re‑compress the raw result.

    Parameters
    ----------
    instance_number: int
        The ``tool_call_result_instance_number`` of the iteration to
        modify.
    new_purpose: str
        The new purpose string to inject.

    Returns
    -------
    str
        Confirmation message.
    """

    target: Iteration | None = None
    for it in iterations:
        if getattr(it, "tool_call_result_instance_number", None) == instance_number:
            target = it
            break
            
    if target is None:
        return f"No iteration with instance_number {instance_number} found."

    if target.model_response and target.model_response.tool_calls:
        target.model_response.tool_calls[0].args["purpose"] = new_purpose
    else:
        return f"Iteration {instance_number} has no tool call to update."

    target.compression_limit = None
    target.tool_call_result_chunks = None
    
    return f"Updated purpose of iteration {instance_number} to '{new_purpose}'."
