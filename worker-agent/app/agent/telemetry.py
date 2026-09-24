from datetime import datetime, UTC
import json
import uuid
import requests
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from contracts.inference_contracts.evidence import Evidence

class ToolEvent(BaseModel):
    iteration: int
    event_type: str
    tool: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    
# ---------------------------------------------------------------------------
# Helper: send a tool result to the evidence ingestion endpoint
# ---------------------------------------------------------------------------

def ingest_tool_event(execution_id: str, tool_event: ToolEvent) -> None:
  
    try:
    
        now = datetime.now(UTC).isoformat()

        payload = Evidence(
            evidence_id=str(uuid.uuid4()),
            execution_id=execution_id,
            event_id=f"{execution_id}-{tool_event.iteration}",
            evidence_type=tool_event.tool,          # e.g. "web_search", "read_file"
            content=str(tool_event.result), 
            source_type=tool_event.event_type,
            source_name=tool_event.tool,
            observed_at=now,
            retrieved_at=now,
            metadata={"args": tool_event.args},     # structured, don't lose it
            worker_version="1.0.1",
        )
        resp = requests.post("http://backbone-api:8000/ingest/evidence", json=payload.model_dump(mode="json"), timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[Evidence ingestion] failed for event {tool_event}: {e}")

