from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class DeltaAction(str, Enum):
    APPEND = "append"            # Add as a new distinct item
    REFINE = "refine"            # Update existing text with new nuance
    REPLACE = "replace"          # New info supersedes old info entirely
    RESOLVE = "resolve"          # Hypothesis confirmed/rejected
    FLAG_CONFLICT = "flag_conflict" # Contradictory info found

class ElementDelta(BaseModel):
    latest_id: str = Field(..., description="The ID from LATEST_SUMMARY being processed")
    modifies_id: Optional[str] = Field(None, description="The ID from PRIOR_AGGREGATION being updated, if any")
    text: Optional[str] = Field(None, description="The synthesized text to be placed in memory")
    confidence: float = Field(..., ge=0.0, le=1.0)
    action: DeltaAction

class DistillationDelta(BaseModel):
    new_observations: List[ElementDelta] = Field(default_factory=list)
    updated_observations: List[ElementDelta] = Field(default_factory=list)
    new_understandings: List[ElementDelta] = Field(default_factory=list)
    updated_understandings: List[ElementDelta] = Field(default_factory=list)
    new_hypotheses: List[ElementDelta] = Field(default_factory=list)
    updated_hypotheses: List[ElementDelta] = Field(default_factory=list)
    resolved_hypotheses: List[ElementDelta] = Field(default_factory=list)
    completed_steps: List[ElementDelta] = Field(default_factory=list)
    new_artifacts: List[ElementDelta] = Field(default_factory=list)
    contradictions: List[ElementDelta] = Field(default_factory=list)
    obsolete_context: List[str] = Field(
        default_factory=list, 
        description="List of IDs from PRIOR_AGGREGATION that are no longer relevant"
    )
