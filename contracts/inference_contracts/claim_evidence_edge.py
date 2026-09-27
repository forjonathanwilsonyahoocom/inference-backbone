from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

class ClaimEvidenceEdge(BaseModel):
    evidence_id: str
    claim_id: str
    support: float

    model_name: str
      
    observed_at: datetime
    retrieved_at: datetime

    schema_version: Literal["edge.v1"] = "edge.v1"
