from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class DeltaAction(str, Enum):
    REFINE = "refine"               # Update existing text with new nuance
    RESOLVE = "resolve"             # Hypothesis confirmed/rejected
    FLAG_CONFLICT = "flag_conflict" # Contradictory info found
    RETIRE = "retire"               # remove element from working context

class ElementDelta(BaseModel):
    latest_id: str = Field(None, description="The ID from LATEST_SUMMARY being processed")
    modifies_id: str = Field(None, description="The ID from PRIOR_AGGREGATION being updated")
    text: Optional[str] = Field(None, description="The synthesized text to be placed in memory, if any")
    confidence: float = Field(..., ge=0.0, le=1.0, description="confidence in this element placement")
    action: DeltaAction

class DistillationDelta(BaseModel):
    relations: List[ElementDelta] = Field(default_factory=list)
    
