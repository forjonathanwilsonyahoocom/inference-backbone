from typing import Optional, Dict, List
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem
from contracts.inference_contracts.agent_state import Observation
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction

def project_for_worker(item: ExtendedAgentStateItem[Observation]) -> Optional[str]:
    """
    Per-type worker projection for Observation.

    Returns markdown string for one item, or None if it should not appear
    in the worker's context (e.g., contains RETIRE action).
    """
    # Rule: Never send retired text to the LLM.
    if any(delta.action == DeltaAction.RETIRE for delta in item.deltas):
        return None

    # Rule: Return markdown string with the elements of the contains
    # for each of the deltas: action, latest_id, and text
    
    # If no deltas, return a simple markdown summary of the item
    if not item.deltas:
        return f"- Observation: '{item.contains.statement}' (Source: {item.contains.source}, Confidence: {item.contains.confidence:.2f})"

    # If deltas exist, summarize the item + its deltas
    delta_lines = []
    for delta in item.deltas:
        action_str = delta.action.value.upper()
        latest_id_str = delta.latest_id if delta.latest_id else "N/A"
        text_str = delta.text if delta.text else "N/A"
        delta_lines.append(f"  - Action: {action_str}, Latest ID: {latest_id_str}, Text: {text_str[:50]}...") # Truncate text for brevity
    
    return f"- Observation (ID: {item.id}): '{item.contains.statement}'\n" + "\n".join(delta_lines)

def project_for_delta(item: ExtendedAgentStateItem[Observation]) -> Dict:
    """
    Per-type delta extractor projection for Observation.
    Scaffolding: just model_dump the input.
    """
    # This pass is scaffolding as per intent.
    return item.model_dump()
