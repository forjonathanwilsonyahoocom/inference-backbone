from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    evidence_id: str
    execution_id: str
    event_id: str

    evidence_type: str
    content: str
    content_hash: str

    source_type: str
    source_name: str | None = None
    source_url: str | None = None

    observed_at: datetime
    retrieved_at: datetime
    extraction_method: str | None = None

    parent_evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    worker_version: str
    schema_version: Literal["evidence.v1"] = "evidence.v1"
