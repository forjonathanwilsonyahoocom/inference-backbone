from typing import Dict, List, TypeVar, Generic
from pydantic import BaseModel, Field
from contracts.inference_contracts.agent_state_delta import ElementDelta

T = TypeVar('T', bound=BaseModel)

class ExtendedAgentStateItem(BaseModel, Generic[T]):
    """
    One element of AgentState (Observation, Hypothesis, etc.) plus the
    deltas that have targeted it.

    This is the unit of history. The full item lives in ExtendedAgentState
    and is never mutated. Projections build a NEW squished copy of this
    item for the LLM that needs it, leaving this original untouched.

    Use as ExtendedAgentStateItem[Observation], ExtendedAgentStateItem[Hypothesis], etc.
    The type of `contains` is what the projection code dispatches on.
    """

    deltas: List[ElementDelta] = Field(default_factory=list)
    id: str = None #holds the generated id of the T
    contains: T

class ExtendedAgentState(BaseModel):
    """
    The aggregated AgentState, with delta history attached to each element.

    This is NOT generic. One ExtendedAgentState holds many different
    element types at once — observations, hypotheses, completed steps, etc.
    Each list in state_parts is homogeneous in practice (one type per list),
    enforced by how the list is assembled, not by the type system.

    Assembly: build one list at a time from a List[T] (e.g. List[Observation]),
    wrapping each element in ExtendedAgentStateItem[T]. The type is taken
    from the item being handled.

    Traversal: projection code dispatches on type(item.contains) to pick
    the per-type projection function for that item.

    This object is the source of truth for apply_delta and for projections.
    Projections return new objects. This object is never mutated in place.
    """

    state_parts: Dict[str, List[ExtendedAgentStateItem]] = Field(default_factory=dict)
