import pytest
from ..apply_delta import apply_delta_to_aggregate, _find_extended_item_by_id
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem
from observability.metrics import MetricsWrapper
from pydantic import BaseModel

# Helper mock model
class MockT(BaseModel):
    value: str

# Helper functions

def create_item(item_id: str, contains: MockT, deltas=None) -> ExtendedAgentStateItem:
    return ExtendedAgentStateItem(id=item_id, contains=contains, deltas=deltas or [])


def create_state(parts: dict) -> ExtendedAgentState:
    return ExtendedAgentState(state_parts=parts)


def create_delta(modifies_id: str, action: DeltaAction, text: str = None) -> ElementDelta:
    return ElementDelta(modifies_id=modifies_id, text=text, confidence=0.9, action=action)

@pytest.fixture
def metrics():
    return MetricsWrapper("test", is_mock=True)

# ---------- Tests for DeltaAction types ----------

def test_apply_delta_resolve_action(metrics):
    # Setup aggregate with one item
    item_id = "obs_1_1"
    item = create_item(item_id, MockT(value="old"))
    agg = create_state({"observations": [item]})

    # No new items in latest state
    latest = create_state({})

    delta = create_delta(item_id, DeltaAction.RESOLVE, text="resolved text")
    new_delta = DistillationDelta(relations=[delta])

    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)

    target = next(i for i in new_agg.state_parts["observations"] if i.id == item_id)
    assert len(target.deltas) == 1
    assert target.deltas[0].action == DeltaAction.RESOLVE


def test_apply_delta_flag_conflict_action(metrics):
    item_id = "hyp_2_1"
    item = create_item(item_id, MockT(value="hyp"))
    agg = create_state({"hypotheses": [item]})
    latest = create_state({})
    delta = create_delta(item_id, DeltaAction.FLAG_CONFLICT, text="conflict text")
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
    latest = create_state({})
    delta = create_delta(item_id, DeltaAction.RETIRE, text="retire note")
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
    latest = create_state({})
    delta = create_delta("obs_1", DeltaAction.REFINE, text="refine")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    # Original aggregate unchanged
    assert len(agg.state_parts["observations"][0].deltas) == 0
    # New aggregate has delta
    assert len(new_agg.state_parts["observations"][0].deltas) == 1


def test_apply_delta_ignore_unknown_id(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    latest = create_state({})
    delta = create_delta("nonexistent", DeltaAction.REFINE, text="x")
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    # No delta should be added
    assert len(new_agg.state_parts["observations"][0].deltas) == 0


def test_apply_delta_ignore_none_modifies_id(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    latest = create_state({})
    delta = ElementDelta(modifies_id=None, text="x", confidence=0.9, action=DeltaAction.REFINE)
    new_delta = DistillationDelta(relations=[delta])
    new_agg = apply_delta_to_aggregate(metrics, agg, latest, new_delta)
    assert len(new_agg.state_parts["observations"][0].deltas) == 0


def test_apply_delta_multiple_deltas_same_item(metrics):
    agg = create_state({"observations": [create_item("obs_1", MockT(value="a"))]})
    latest = create_state({})
    delta1 = create_delta("obs_1", DeltaAction.REFINE, text="t1")
    delta2 = create_delta("obs_1", DeltaAction.RESOLVE, text="t2")
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

