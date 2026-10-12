from datetime import datetime, UTC
import json
import requests
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from contracts.inference_contracts.evidence import Evidence
from contracts.inference_contracts.agent_state import AgentState
from contracts.inference_contracts.task import Task
from contracts.inference_contracts.final_answer import FinalAnswer

class ToolEvent(BaseModel):
    iteration: int
    instance_number: int | None = None
    event_type: str
    model_name: str
    tool: str | None = "no_tool"
    args: Dict[str, Any] = Field(default_factory=dict)
    result: Any = "no_result"
    
# ---------------------------------------------------------------------------
# Helper: send a tool result to the evidence ingestion endpoint
# ---------------------------------------------------------------------------

def ingest_tool_event(execution_id: str, tool_event: ToolEvent) -> None:
  
    try:
    
        now = datetime.now(UTC).isoformat()

        payload = Evidence(
            evidence_id=f"{execution_id}-{tool_event.instance_number}",
            execution_id=execution_id,
            instance_number=tool_event.instance_number,
            iteration=tool_event.iteration,
            model_name=tool_event.model_name,
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


def ingest_agent_state(state: AgentState) -> None:
  
    try:
        state.state_id = f"{state.execution_id}-{state.instance_number}"
   
        resp = requests.post("http://backbone-api:8000/ingest/agent_state", json=state.model_dump(mode="json"), timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[AgentState ingestion] failed for state {state}: {e}")


def ingest_task(execution_id: str, instruction: str, model_name: str) -> None:

    now = datetime.now(UTC).isoformat()
    
    task = Task(task_id=f"{execution_id}-1",
                execution_id=execution_id,
                instance_number=1,
                content=instruction,
                model_name=model_name,
                observed_at=now,
            )
    
    try:
        resp = requests.post("http://backbone-api:8000/ingest/task", json=task.model_dump(mode="json"), timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[Task ingestion] failed for task {task}: {e}")

def ingest_final_answer(execution_id: str, answer: str, model_name: str) -> None:
  
    now = datetime.now(UTC).isoformat()
    
    final_answer = FinalAnswer(final_answer_id=f"{execution_id}-1",
                       execution_id=execution_id,
                       instance_number=1,
                       content=answer,
                       model_name=model_name,
                       observed_at=now,
                    )
    try:
        final_answer.final_answer_id = f"{final_answer.execution_id}-{final_answer.instance_number}"
   
        resp = requests.post("http://backbone-api:8000/ingest/final_answer", json=final_answer.model_dump(mode="json"), timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[FinalAnswer ingestion] failed for final_answer {final_answer}: {e}")

