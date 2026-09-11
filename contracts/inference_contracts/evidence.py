# inference_contracts/evidence.py
"""Evidence data model.

The JSON‑Schema is kept in ``contracts/evidence/v1/schema.json``.
We load it at import time and use it to create a :class:`pydantic.BaseModel`
that mirrors the schema.  The model is intentionally simple – it only
contains the fields defined in the schema – but it can be extended with
custom validators or methods if needed.

The module also exposes a helper :func:`validate_json` that can be used
in CI to ensure that a JSON payload conforms to the schema.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict

from pydantic import BaseModel, Field
from jsonschema import Draft7Validator, ValidationError

# Resolve the path to the schema relative to this file.
_SCHEMA_PATH = pathlib.Path(__file__).resolve().parent.parent / "evidence" / "v1" / "schema.json"

# Load the schema once at import time.
with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
    _SCHEMA: Dict[str, Any] = json.load(f)

# Create a Pydantic model that matches the schema.
# We map JSON‑Schema types to Pydantic field types.
class Evidence(BaseModel):
    chunk_count: int = Field(..., description="Number of chunks in the evidence set")
    chunk_index: int = Field(..., description="Index of this chunk within the set")
    content: str = Field(..., description="Raw content of the chunk")
    content_hash: str = Field(..., description="Hash of the content for deduplication")
    embedding_model: str = Field(..., description="Name of the embedding model used")
    embedding_task: str = Field(..., description="Task the embedding was generated for")
    event_id: str = Field(..., description="Identifier of the event that produced the evidence")
    evidence_id: str = Field(..., description="Unique identifier for this evidence chunk")
    execution_id: str = Field(..., description="Identifier of the execution that produced the evidence")
    source_name: str = Field(..., description="Human‑readable name of the source")
    source_type: str = Field(..., description="Type of the source (e.g., pdf, url, db)")
    source_url: str = Field(..., description="URL of the source, validated as a URI")

    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = _SCHEMA

# Helper to validate arbitrary JSON against the schema.
_validator = Draft7Validator(_SCHEMA)


def validate_json(data: Dict[str, Any]) -> None:
    """Validate *data* against the JSON‑Schema.

    Raises :class:`jsonschema.ValidationError` if the data is invalid.
    """
    _validator.validate(data)

__all__ = ["Evidence", "validate_json"]

