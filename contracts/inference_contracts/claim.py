from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str
    instance_number: int # numbering within the execution
    importance: float
    execution_id: str

    content: str
    content_hash: str | None = None

    model_name: str
        
    observed_at: datetime
    retrieved_at: datetime

    embedding_model: str | None = None
    
    validator_version: str
    schema_version: Literal["claim.v1"] = "claim.v1"
