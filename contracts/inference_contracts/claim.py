from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str
    execution_id: str

    content: str
    content_hash: str | None = None

    observed_at: datetime
    retrieved_at: datetime
    
    metadata: dict[str, Any] = Field(default_factory=dict)

    worker_version: str
    schema_version: Literal["claim.v1"] = "claim.v1"
