from contracts.inference_contracts.agent_state import AgentState
from agent.extend_agent_state import extend_state
from observability.metrics import MetricsWrapper
import pytest

@pytest.fixture
def metrics():
    return MetricsWrapper("test", is_mock=True)
    
def get_state_1():
    return AgentState(
        observations=[],
        artifacts=[
            {"location": "some/path/to_file.py", "type": "file", "value": "some text"}
        ],
        understandings=[],
        hypotheses=[],
        completed_steps=[],
    )


def test_extend_state(metrics):
    extended = extend_state(metrics, 1, get_state_1())

    assert "art_1_0" == extended.state_parts["artifacts"][0].id
    assert 0 == len(extended.state_parts["understandings"])

