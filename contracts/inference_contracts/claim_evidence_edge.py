from datetime import datetime
from typing import Any, Literal

from contracts.inference_contracts.validations import ArtifactId
from pydantic import BaseModel, Field

class ClaimEvidenceEdge(BaseModel):
    evidence_id: ArtifactId
    claim_id: ArtifactId
    support: float

    model_name: str
      
    observed_at: datetime
    retrieved_at: datetime

    schema_version: Literal["edge.v1"] = "edge.v1"
