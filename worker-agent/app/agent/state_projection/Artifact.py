from typing import Optional, Dict
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem
from contracts.inference_contracts.agent_state import Artifact

def project_for_worker(item: ExtendedAgentStateItem[Artifact]) -> Optional[str]:
    """
    Worker projection: returns markdown for one item, or None if it should not appear.
    Returns None if the part contains at least one RETIRE action DeltaElement.
    """
    if any(delta.action == "RETIRE" for delta in item.deltas):
        return None

    # Return markdown string with element details
    return f"Artifact ID: {item.id} | Type: {item.contains.type} | Location: {item.contains.location} | Value Snippet: {item.contains.value[:50]}..."

def project_for_delta(item: ExtendedAgentStateItem[Artifact]) -> Dict:
    """
    Delta extractor projection: currently just model_dump the input (scaffolding).
    """
    return item.model_dump()
