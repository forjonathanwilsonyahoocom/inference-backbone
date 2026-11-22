from typing import Dict, Generic, List, TypeVar
from pydantic import BaseModel, Field
T = TypeVar('T')
from contracts.inference_contracts.agent_state_delta import ElementDelta

class ExtendedAgentState(BaseModel):
    """
    this class will represent the aggregated AgentState structure along with the AgentStateDelta applied to it
    we will keep this class as general as possible so that it does not become 
    a coupled maintenance hazard, we will project this class to a markdown report visible to
    the main worker agent llm
    
    we will show this to the delta extraction llm
    """
    state_parts: Dict[str, List[ExtendedAgentStateItem]]
    
class ExtendedAgentStateItem(BaseModel, Generic[T]):
    """
    this class will hold an AgentState element
        Observation,
        Hypothesis,
        etc...
    with the list of ElementDelta targeting it
    we will use the contained type as a hint to the 
    report projection code

    """
    deltas: List[ElementDelta] = Field(default_factory=list)
    contains: T
