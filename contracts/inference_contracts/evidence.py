from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class Evidence(BaseModel):
    evidence_id: str
    execution_id: str
    event_id: str

    content: str
    content_hash: str

    source_type: str
    source_name: Optional[str] = None
    source_url: Optional[str] = None

    observed_at: datetime
    retrieved_at: datetime

    extraction_method: str

    parent_evidence_ids: List[str] = []

    metadata: Dict[str, Any] = {}

    worker_version: str
    schema_version: Literal["evidence.v1"] = "evidence.v1"

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        return cls(**data)

    @classmethod
    def schema_json(cls) -> str:
        return super().schema_json()

    @classmethod
    def schema_dict(cls) -> Dict[str, Any]:
        return super().schema()

