from ..apply_delta import apply_delta
from observability.metrics import MetricsWrapper
import pytest

def get_state_1():
    return {
    "observations": [
    ],
    "artifacts": [
    ],
    "understandings": [
    ],
    "hypotheses": [
    ],
    "completed_steps": [
    ]
  }

def get_aggregate_1():
    return {
    "artifacts": [],
    "observations": [],
    "understandings": [],
    "hypotheses": [],
    "completed_steps": [
      {
        "id" : "com_1_1",
        "step": "Read agent_state_delta.py and agent_state.py",
        "result": "Success",
        "confidence": 1.0
      }
    ]
  }

def get_delta_1():
    return {
    "observations": [],
    "understandings": [],
    "hypotheses": [],
    "completed_steps": [],
    "artifacts": [
      {
        "latest_id": "art_30_1",
        "modifies_id": None,
        "text": "if iteration.iteration > compact.upto\nif iteration.iteration < last_upto\nif iteration.iteration <= last_upto",
        "confidence": 1.0,
        "action": "append"
      }
    ],
    "obsolete_context": [
      "obs_30_1",
      "com_30_3"
    ]
  }


def test_apply_delta():
    metrics = MetricsWrapper("test-worker-agent")
    
    updated = apply_delta(metrics, get_aggregate_1(), get_state_1(), get_delta_1() )
    print(updated)
    
    
