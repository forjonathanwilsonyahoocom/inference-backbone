from typing import Dict, List
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem

# Helper to convert a plain dict representation of AgentState into ExtendedAgentState

def dict_to_extended(state_dict: Dict[str, List[Dict]]) -> ExtendedAgentState:
    """Wrap a raw AgentState dict into an ExtendedAgentState.

    Each top‑level key (artifacts, observations, …) becomes a
    ``state_parts`` entry containing a list of ``ExtendedAgentStateItem``.
    The ``contains`` field holds the original dict, and ``deltas`` is
    initialised empty.
    """
    parts: Dict[str, List[ExtendedAgentStateItem]] = {}
    for key, items in state_dict.items():
        parts[key] = [ExtendedAgentStateItem(contains=item, deltas=[]) for item in items]
    return ExtendedAgentState(state_parts=parts)

# Helper to flatten an ExtendedAgentState back into the plain dict format

def extended_to_dict(ext: ExtendedAgentState) -> Dict[str, List[Dict]]:
    """Return the underlying dict representation of an ExtendedAgentState.

    The function simply extracts the ``contains`` field from each
    ``ExtendedAgentStateItem``.
    """
    return {k: [item.contains for item in v] for k, v in ext.state_parts.items()}
