from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel


class EvidenceChunk(BaseModel):
    chunk_id: str
    evidence_id: str

    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str
    embedding_task: str

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceChunk":
        return cls(**data)

    @classmethod
    def schema_json(cls) -> str:
        return super().schema_json()

    @classmethod
    def schema_dict(cls) -> Dict[str, Any]:
        return super().schema()

