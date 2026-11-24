from typing import Dict, List

from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem, ExtendedAgentState

from agent.state_projection.projection_dispatcher import project_for_worker, project_for_delta
from contracts.inference_contracts.agent_state import Artifact, CompletedStep, Observation, Understanding, Hypothesis

def create_mock_item(contains, deltas: List[ElementDelta], item_id: str) -> ExtendedAgentStateItem:
    """Helper to create a mock ExtendedAgentStateItem."""
    return ExtendedAgentStateItem(
        deltas=deltas,
        id=item_id,
        contains=contains
    )

    
def test_full_state_projection():
    """Test combined worker and delta projections across multiple state parts (Observation and Hypothesis)."""
    
    # 1. Setup mock types
    mock_observation = Observation(statement = "Obs test statement",
                                    source = "test source",
                                    confidence = 0.95)
    mock_hypothesis = Hypothesis(hypothesis = "Hyp test hypothesis",
                                  source = "test source",
                                  status = "pending",
                                  confidence = 0.9)

    # 2. Setup mock deltas
    mock_delta_no_retire = ElementDelta(action = DeltaAction.REFINE,
                                        confidence = 0.9,
                                        latest_id = "l_1",
                                        text = "refined text snippet")
    mock_delta_retire = ElementDelta(action = DeltaAction.RETIRE,
                                     confidence = 0.9)

    # 3. Create items
    # Item 1 (Observation, safe)
    item_obs_safe = create_mock_item(mock_observation, [mock_delta_no_retire], "obs_1_1")
    # Item 2 (Observation, retired)
    item_obs_retired = create_mock_item(mock_observation, [mock_delta_retire], "obs_1_2")
    # Item 3 (Hypothesis, safe)
    item_hyp_safe = create_mock_item(mock_hypothesis, [mock_delta_no_retire], "hyp_1_1")

    # 4. Build ExtendedAgentState (State with 2 populated parts)
    state_parts: Dict[str, List[ExtendedAgentStateItem]] = {
        "observations": [item_obs_safe, item_obs_retired],
        "hypotheses": [item_hyp_safe]
    }
    extended_state = ExtendedAgentState(state_parts=state_parts)

    # 5. Test Worker Projection (Should only include safe items)
    worker_output = project_for_worker(extended_state)
    assert worker_output is not None
    # Check that both safe items contribute to the summary
    assert "Obs test statement" in worker_output
    assert "Hyp test hypothesis" in worker_output
    # Check that the retired item is correctly excluded
    assert "obs_1_2" not in worker_output

    # 6. Test Delta Projection (Scaffolding for delta extraction)
    delta_output = project_for_delta(extended_state)
    assert isinstance(delta_output, dict)
    # Check that both parts are present in the delta output
    assert "observations" in delta_output
    assert "hypotheses" in delta_output
    # Check that only safe items (non-retired) are included in the delta scaffolding
    assert "obs_1_1" in delta_output["observations"]
    assert "obs_1_2" not in delta_output["observations"]
    assert "hyp_1_1" in delta_output["hypotheses"]

