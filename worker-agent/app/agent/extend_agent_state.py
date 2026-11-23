from contracts.inference_contracts.agent_state_extended import (
    ExtendedAgentState,
    ExtendedAgentStateItem,
)
from typing import Any
from contracts.inference_contracts.agent_state import AgentState

def extend_item(iteration_id: int, 
                item_id: int,
                state_part: Any) -> ExtendedAgentStateItem:
    t = type(state_part)
    return ExtendedAgentStateItem[t](
        id=f"{t.__name__.lower()[:3]}_{iteration_id}_{item_id}",
        contains=state_part,
    )


def extend_state(iteration_id: int, 
                 agent_state: AgentState) -> ExtendedAgentState:
    extended = ExtendedAgentState()
    for name, value in agent_state:
        extended.state_parts[name] = []
        for i, item in enumerate(value):
            extended.state_parts[name].append(extend_item(iteration_id, i, item))

    return extended



