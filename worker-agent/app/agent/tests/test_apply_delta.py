import pytest
from ..apply_delta import apply_delta_to_aggregate, _find_extended_item_by_id
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem
from pprint import pprint
from typing import Any
from pydantic import BaseModel

# Minimal mock models for testing
class MockT(BaseModel):
    value: Any

def create_item(item_id: str, contains: MockT, deltas: list = None) -> ExtendedAgentStateItem:
    return ExtendedAgentStateItem(id=item_id, contains=contains, deltas=deltas or [])

def create_state(state_parts: dict) -> ExtendedAgentState:
    return ExtendedAgentState(state_parts=state_parts)

def create_delta(modifies_id: str, latest_id: str, action: DeltaAction, text: str = None) -> ElementDelta:
    return ElementDelta(modifies_id=modifies_id, latest_id=latest_id, text=text, confidence=0.9, action=action)

@pytest.fixture
def metrics():
    return MetricsWrapper("test", is_mock=True)

# ---------- Tests for mixed DeltaAction types ----------

def test_apply_delta_to_aggregate_success(metrics: MetricsWrapper):
    # 1. Setup initial state (Last Aggregate)
    # Item A (to be modified)
    item_a_id = "obs_1_1"
    item_a = create_item(item_a_id, MockT(value="Initial A"), deltas=[])
    # Item B (unmodified)
    item_b_id = "hyp_2_1"
    item_b = create_item(item_b_id, MockT(value="Initial B"), deltas=[])
    
    last_aggregate = create_state({
        "observations": [item_a, item_b]
    })

    # 2. Setup latest state (New incoming data)
    # New Item C (new, no delta)
    item_c_id = "obs_3_3"
    item_c = create_item(item_c_id, MockT(value="New C"))
    # New Item D (new, no delta)
    item_d_id = "hyp_4_4"
    item_d = create_item(item_d_id, MockT(value="New D"))
    
    latest_extended_state = create_state({
        "observations": [item_c],
        "hypotheses": [item_d]
    })

    # 3. Setup new delta
    # Delta targets Item A
    delta_a = create_delta(item_a_id, item_c_id, DeltaAction.REFINE, text="Refined A text")
    new_delta = DistillationDelta(
        relations= [delta_a]
    )

    # 4. Execute
    new_aggregate = apply_delta_to_aggregate(metrics, last_aggregate, latest_extended_state, new_delta)

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
    

# ---------- Tests for DeltaAction types ----------

def test_apply_delta_resolve_action(metrics):
    # Setup aggregate with one item
    item_id = "obs_1_1"
    item = create_item(item_id, MockT(value="old"))
    agg = create_state({"observations": [item]})

    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})

    delta = create_delta(item_id, item_id2, DeltaAction.RESOLVE, text="resolved text")
    new_delta = DistillationDelta(relations=[delta])

    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)

    target = next(i for i in new_agg.state_parts["observations"] if i.id == item_id)
    assert len(target.deltas) == 1
    assert target.deltas[0].action == DeltaAction.RESOLVE


def test_apply_delta_flag_conflict_action(metrics):
    item_id = "hyp_2_1"
    item = create_item(item_id, MockT(value="hyp"))
    agg = create_state({"hypotheses": [item]})
    
    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})

    delta = create_delta(item_id, item_id2, DeltaAction.FLAG_CONFLICT, text="conflict text")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    target = next(i for i in new_agg.state_parts["hypotheses"] if i.id == item_id)
    assert len(target.deltas) == 1
    assert target.deltas[0].action == DeltaAction.FLAG_CONFLICT

# ---------- Tests for RETIRE action ----------

def test_apply_delta_retire_action(metrics):
    item_id = "art_1_1"
    item = create_item(item_id, MockT(value="artifact"))
    agg = create_state({"artifacts": [item]})

    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})
    
    delta = create_delta(item_id,item_id2,  DeltaAction.RETIRE, text="retire note")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    target = next(i for i in new_agg.state_parts["artifacts"] if i.id == item_id)
    assert len(target.deltas) == 1
    assert target.deltas[0].action == DeltaAction.RETIRE

# ---------- Tests for apply_delta behavior ----------

def test_apply_delta_adds_new_items(metrics):
    agg = create_state({"observations": []})
    new_item = create_item("obs_3_1", MockT(value="new"))
    latest = create_state({"observations": [new_item]})
    new_delta = DistillationDelta(relations=[])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    assert len(new_agg.state_parts["observations"]) == 1
    assert new_agg.state_parts["observations"][0].id == "obs_3_1"


def test_apply_delta_immutability(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
   
    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})
    
    delta = create_delta("obs_1", item_id2, DeltaAction.REFINE, text="refine")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    # Original aggregate unchanged
    assert len(agg.state_parts["observations"][0].deltas) == 0
    # New aggregate has delta
    assert len(new_agg.state_parts["observations"][0].deltas) == 1


def test_apply_delta_ignore_unknown_id(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    
    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})
    
    delta = create_delta("nonexistent", item_id2, DeltaAction.REFINE, text="x")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    # No delta should be added
    assert len(new_agg.state_parts["observations"][0].deltas) == 0


def test_apply_delta_both_ids_must_exist(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    latest = create_state({})
    delta = ElementDelta(modifies_id="obs_not_there", latest_id="obs_1", text="x", confidence=0.9, action=DeltaAction.REFINE)
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    assert len(new_agg.state_parts["observations"][0].deltas) == 0


def test_apply_delta_multiple_deltas_same_item(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    item_id2 = "art_2_1"
    item2 = create_item(item_id2, MockT(value="new"))
    # No new items in latest state
    latest = create_state({"artifacts": [item2]})
    delta1 = create_delta("obs_1", item_id2, DeltaAction.REFINE, text="t1")
    delta2 = create_delta("obs_1", item_id2, DeltaAction.RESOLVE, text="t2")
    new_delta = DistillationDelta(relations=[delta1, delta2])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    target = new_agg.state_parts["observations"][0]
    assert len(target.deltas) == 2
    actions = {d.action for d in target.deltas}
    assert DeltaAction.REFINE in actions and DeltaAction.RESOLVE in actions

# ---------- Tests for _find_extended_item_by_id ----------

def test_find_item_by_id_success(metrics):
    item = create_item("obs_1_1", MockT(value="x"))
    agg = create_state({"observations": [item]})
    found = _find_extended_item_by_id(agg, "obs_1_1")
    assert found is not None
    assert found.id == "obs_1_1"


def test_find_item_by_id_not_found(metrics):
    agg = create_state({"observations": []})
    found = _find_extended_item_by_id(agg, "obs_1_1")
    assert found is None

