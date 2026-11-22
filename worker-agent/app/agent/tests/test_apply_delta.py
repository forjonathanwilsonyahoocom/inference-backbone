from ..apply_delta import apply_delta
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
import pytest
from pprint import pprint


def get_state_1():
    return {
        "observations": [
    ],
        "artifacts": [
        {
        "id": "art_1_1",
        "location": "some/path/to_file.py",
        "type": "file",
        "value": "some text"
    }
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
        "observations": [{
        "id": "obs_1_1",
        "statement": "Compression is deterministic and idempotent and does not mutate raw Iteration values; only *_compressed fields are written.",
        "source": "inference-backbone/worker-agent/app/agent/compression.py",
        "confidence": 0.95
    }],
        "understandings": [],
        "hypotheses": [],
        "completed_steps": [
        {
        "id": "com_1_1",
        "step": "Read agent_state_delta.py and agent_state.py",
        "result": "Success",
        "confidence": 1.0
    }
    ]
    }


def get_delta_1():
    return DistillationDelta(observations=[ElementDelta(action=DeltaAction.RETIRE, modifies_id="obs_1_1", confidence=1.0)],
        understandings=[],
        hypotheses=[],
        completed_steps=[ElementDelta(action=DeltaAction.RETIRE, modifies_id="com_1_1", confidence=1.0)],
        artifacts=[ElementDelta(action=DeltaAction.APPEND, latest_id="art_1_1", text="some text", confidence=1.0)]
    )


def test_apply_delta():
    metrics = MetricsWrapper("test-worker-agent", is_mock=True)

    updated = apply_delta(metrics, get_aggregate_1(), get_state_1(), get_delta_1())

    assert len(updated["completed_steps"]) == 0

    assert len(updated["observations"]) == 0

    assert len(updated["artifacts"]) == 1

   # pprint(updated)

