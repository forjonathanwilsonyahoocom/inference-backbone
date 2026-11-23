from typing import Optional, Dict
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem
from contracts.inference_contracts.agent_state import CompletedStep
from contracts.inference_contracts.agent_state_delta import DeltaAction

def project_for_worker(item: ExtendedAgentStateItem[CompletedStep]) -> Optional[str]:
    """
    Worker projection: returns markdown for one item, or None if it should not appear.
    Returns None if the part contains at least one RETIRE action DeltaElement.
    """
    if any(delta.action == DeltaAction.RETIRE for delta in item.deltas):
        return None

    # Return markdown string with element details
    return (
        f"Completed Step ID: {item.id} | Step: {item.contains.step} | "
        f"Confidence: {item.contains.confidence:.2f} | Result Snippet: {item.contains.result[:50]}..."
    )

def project_for_delta(item: ExtendedAgentStateItem[CompletedStep]) -> Dict:
    """
    Delta extractor projection: currently just model_dump the input (scaffolding).
    """
    return item.model_dump()
