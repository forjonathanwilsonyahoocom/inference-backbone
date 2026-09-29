from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    evidence_id: str
    execution_id: str
    instance_number: int # numbering within the execution
    iteration: int

    evidence_type: str
    content: str
    content_hash: str | None = None

    model_name: str
    
    source_type: str
    source_name: str | None = None
    
    observed_at: datetime
    retrieved_at: datetime
    extraction_method: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)

    worker_version: str
    schema_version: Literal["evidence.v1"] = "evidence.v1"
