from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class DeltaAction(str, Enum):
    APPEND = "append"            # Add as a new distinct item
    REFINE = "refine"            # Update existing text with new nuance
    REPLACE = "replace"          # New info supersedes old info entirely
    RESOLVE = "resolve"          # Hypothesis confirmed/rejected
    FLAG_CONFLICT = "flag_conflict" # Contradictory info found
    RETIRE = "retire"            #remove element from working context

class ElementDelta(BaseModel):
    latest_id: Optional[str] = Field(None, description="The ID from LATEST_SUMMARY being processed, if any")
    modifies_id: Optional[str] = Field(None, description="The ID from PRIOR_AGGREGATION being updated, if any")
    text: Optional[str] = Field(None, description="The synthesized text to be placed in memory, if any")
    confidence: float = Field(..., ge=0.0, le=1.0, description="confidence in this element placement")
    action: DeltaAction

class DistillationDelta(BaseModel):
    observations: List[ElementDelta] = Field(default_factory=list)
    understandings: List[ElementDelta] = Field(default_factory=list)
    hypotheses: List[ElementDelta] = Field(default_factory=list)
    completed_steps: List[ElementDelta] = Field(default_factory=list)
    artifacts: List[ElementDelta] = Field(default_factory=list)
    obsolete_context: List[ElementDelta] = Field(default_factory=list)
    
