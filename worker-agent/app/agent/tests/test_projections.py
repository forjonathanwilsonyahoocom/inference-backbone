from typing import Dict, List
from unittest.mock import Mock
from contracts.inference_contracts.agent_state_extended import ExtendedAgentStateItem
from contracts.inference_contracts.agent_state import Artifact, CompletedStep
from inference_backbone.worker_agent.app.agent.state_projection.Artifact import project_for_worker as proj_worker_artifact, project_for_delta as proj_delta_artifact
from inference_backbone.worker_agent.app.agent.state_projection.CompletedStep import project_for_worker as proj_worker_completed, project_for_delta as proj_delta_completed

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
    mock_artifact = Mock(spec=Artifact)
    mock_artifact.type = "file"
    mock_artifact.location = "test/path"
    mock_artifact.value = "test content snippet"

    # Setup mock deltas
    mock_delta_no_retire = Mock()
    mock_delta_no_retire.action = "refine"

    mock_delta_retire = Mock()
    mock_delta_retire.action = "retire"

    # Test case 1: No RETIRE -> Should return markdown
    item_safe = create_mock_item(mock_artifact, [mock_delta_no_retire], "a1")
    worker_output_safe = proj_worker_artifact(item_safe)
    assert worker_output_safe is not None
    assert "Artifact ID: a1" in worker_output_safe

    # Test case 2: Contains RETIRE -> Should return None
    item_retired = create_mock_item(mock_artifact, [mock_delta_retire], "a2")
    worker_output_retired = proj_worker_artifact(item_retired)
    assert worker_output_retired is None

    # Test delta projection (scaffolding)
    delta_output = proj_delta_artifact(item_safe)
    assert isinstance(delta_output, dict)

def test_completed_step_projection():
    """Test worker and delta projections for CompletedStep."""
    # Setup mock types
    mock_step = Mock(spec=CompletedStep)
    mock_step.step = "test step"
    mock_step.result = "test result snippet"
    mock_step.confidence = 0.95

    # Setup mock deltas
    mock_delta_no_retire = Mock()
    mock_delta_no_retire.action = "refine"

    mock_delta_retire = Mock()
    mock_delta_retire.action = "retire"

    # Test case 1: No RETIRE -> Should return markdown
    item_safe = create_mock_item(mock_step, [mock_delta_no_retire], "com1")
    worker_output_safe = proj_worker_completed(item_safe)
    assert worker_output_safe is not None
    assert "Completed Step ID: com1" in worker_output_safe

    # Test case 2: Contains RETIRE -> Should return None
    item_retired = create_mock_item(mock_step, [mock_delta_retire], "com2")
    worker_output_retired = proj_worker_completed(item_retired)
    assert worker_output_retired is None

    # Test delta projection (scaffolding)
    delta_output = proj_delta_completed(item_safe)
    assert isinstance(delta_output, dict)

# Note: To run these tests, the imports must resolve correctly within the workspace.
# We assume the project structure allows for these relative imports.
