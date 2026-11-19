from typing import Dict, List, Any, Literal
from pydantic import BaseModel, Field, ConfigDict

# --- LLM-visible, unchanged ---
# AgentState and AgentStateDelta stay exactly as you have them.
# The LLM never sees anything below this line.

# --- Fold-visible, new ---

class MetaEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="UUID for this meta entry")
    type: Literal["provenance", "refine", "superseded", "resolve", "conflict", "retraction", "annotation"]
    target_id: str = Field(..., description="ID in PRIOR_AGGREGATION being affected, or latest_id if no target")
    source_id: str = Field(..., description="ID in LATEST_SUMMARY that justified this change")
    target_type: str = Field(..., description="Section: artifacts | observations | understandings | hypotheses | completed_steps")
    text: str = Field(..., description="Human-readable record of what happened")
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_by: str = Field(default="fold")
    source_delta_action: str = Field(..., description="DeltaAction that created this entry")
    # Add execution_uuid, created_at in your real code — omitted here for brevity

class FoldManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fold_version: str
    llm_schema_version: str
    aggregate_version: int

class AgentStateExtended(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: Dict[str, List[Dict[str, Any]]]
    meta_entries: List[MetaEntry] = Field(default_factory=list)
    manifest: FoldManifest
