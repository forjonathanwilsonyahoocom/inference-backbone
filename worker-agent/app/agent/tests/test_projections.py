from typing import Dict, List

from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem
from contracts.inference_contracts.agent_state import Artifact, CompletedStep
from agent.state_projection.Artifact import project_for_worker as proj_worker_artifact, project_for_delta as proj_delta_artifact
from agent.state_projection.CompletedStep import project_for_worker as proj_worker_completed, project_for_delta as proj_delta_completed

def create_mock_item(contains, deltas: List[Mock], item_id: str) -> ExtendedAgentStateItem:
    """Helper to create a mock ExtendedAgentStateItem."""
    return ExtendedAgentStateItem(
        deltas=deltas,
        id=item_id,
        contains=contains
    )

def test_artifact_projection():
    """Test worker and delta projections for Artifact."""
    # Setup mock types
    mock_artifact = Artifact(type = "file",
                             location = "test/path",
                             value = "test content snippet")

    # Setup mock deltas
    mock_delta_no_retire = ElementDelta(action = DeltaAction.REFINE,
                                        confidence = 0.9)

    mock_delta_retire = ElementDelta(action = DeltaAction.RETIRE,
                                     confidence = 0.9)

    # Test case 1: No RETIRE -> Should return markdown
    item_safe = create_mock_item(mock_artifact, [mock_delta_no_retire], "art_1_1")
    worker_output_safe = proj_worker_artifact(item_safe)
    assert worker_output_safe is not None
    assert "Artifact ID: art_1_1" in worker_output_safe

    # Test case 2: Contains RETIRE -> Should return None
    item_retired = create_mock_item(mock_artifact, [mock_delta_retire], "art_1_2")
    worker_output_retired = proj_worker_artifact(item_retired)
    assert worker_output_retired is None

    # Test delta projection (scaffolding)
    delta_output = proj_delta_artifact(item_safe)
    assert isinstance(delta_output, dict)

def test_completed_step_projection():
    """Test worker and delta projections for CompletedStep."""
    # Setup mock types
    mock_step = CompletedStep(step = "test step",
                              result = "test result snippet",
                              confidence = 0.95)

    # Setup mock deltas
    mock_delta_no_retire =ElementDelta(action = DeltaAction.REFINE,
                                       confidence = 0.9)

    mock_delta_retire =  ElementDelta(action = DeltaAction.RETIRE,
                                      confidence = 0.9)

    # Test case 1: No RETIRE -> Should return markdown
    item_safe = create_mock_item(mock_step, [mock_delta_no_retire], "com_1_1")
    worker_output_safe = proj_worker_completed(item_safe)
    assert worker_output_safe is not None
    assert "Completed Step ID: com_1_1" in worker_output_safe

    # Test case 2: Contains RETIRE -> Should return None
    item_retired = create_mock_item(mock_step, [mock_delta_retire], "com_1_2")
    worker_output_retired = proj_worker_completed(item_retired)
    assert worker_output_retired is None

    # Test delta projection (scaffolding)
    delta_output = proj_delta_completed(item_safe)
    assert isinstance(delta_output, dict)

# Note: To run these tests, the imports must resolve correctly within the workspace.
# We assume the project structure allows for these relative imports.
