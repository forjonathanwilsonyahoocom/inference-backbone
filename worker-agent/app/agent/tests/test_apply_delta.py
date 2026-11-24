import pytest
from ..apply_delta import apply_delta_to_aggregate
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem
from pprint import pprint
from typing import Any
from pydantic import BaseModel

# Minimal mock models for testing
class MockT(BaseModel):
    value: Any

def create_mock_item(item_id: str, contains: MockT, deltas: list = None) -> ExtendedAgentStateItem:
    return ExtendedAgentStateItem(id=item_id, contains=contains, deltas=deltas or [])

def create_mock_state(state_parts: dict) -> ExtendedAgentState:
    return ExtendedAgentState(state_parts=state_parts)

def create_mock_delta(modifies_id: str, action: DeltaAction, text: str = None) -> ElementDelta:
    return ElementDelta(modifies_id=modifies_id, text=text, confidence=0.9, action=action)

@pytest.fixture
def mock_metrics():
    return MetricsWrapper("test", is_mock=True)

def test_apply_delta_to_aggregate_success(mock_metrics: MetricsWrapper):
    # 1. Setup initial state (Last Aggregate)
    # Item A (to be modified)
    item_a_id = "obs_1_1"
    item_a = create_mock_item(item_a_id, MockT(value="Initial A"), deltas=[])
    # Item B (unmodified)
    item_b_id = "hyp_2_1"
    item_b = create_mock_item(item_b_id, MockT(value="Initial B"), deltas=[])
    
    last_aggregate = create_mock_state({
        "observations": [item_a, item_b]
    })

    # 2. Setup latest state (New incoming data)
    # New Item C (new, no delta)
    item_c_id = "obs_3_3"
    item_c = create_mock_item(item_c_id, MockT(value="New C"))
    # New Item D (new, no delta)
    item_d_id = "hyp_4_4"
    item_d = create_mock_item(item_d_id, MockT(value="New D"))
    
    latest_extended_state = create_mock_state({
        "observations": [item_c],
        "hypotheses": [item_d]
    })

    # 3. Setup new delta
    # Delta targets Item A
    delta_a = create_mock_delta(item_a_id, DeltaAction.REFINE, text="Refined A text")
    new_delta = DistillationDelta(
        relations= [delta_a]
    )

    # 4. Execute
    new_aggregate = apply_delta_to_aggregate(mock_metrics, last_aggregate, latest_extended_state, new_delta)

    # 5. Assertions
    
    # Check that new items are present
    assert len(new_aggregate.state_parts["observations"]) == 3 # A, B, C
    assert len(new_aggregate.state_parts["hypotheses"]) == 1 # D
    
    # Check that the targeted item A has the new delta
    target_item_a = next(item for item in new_aggregate.state_parts["observations"] if item.id == item_a_id)
    assert len(target_item_a.deltas) == 1
    assert target_item_a.deltas[0].action == DeltaAction.REFINE
    
    # Check immutability: original items should not have been modified
    assert len(item_a.deltas) == 0
    
    # Check that the original aggregate is unchanged
    assert len(last_aggregate.state_parts["observations"]) == 2 # A, B
    
    # Check that the new aggregate is a distinct object
    assert id(new_aggregate) != id(last_aggregate)
    
    print("Test Success: Aggregation and immutability verified.")
