import pytest
from ..apply_delta import apply_delta
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper


def get_aggregate():
    return {
        "artifacts": [
            {"id": "art_1", "location": "path1", "type": "file", "value": "text1"}
        ],
        "observations": [
            {"id": "obs_1", "statement": "s1"}
        ],
        "understandings": [
            {"id": "und_1", "detail": "d1"}
        ],
        "hypotheses": [
            {"id": "hyp_1", "status": "unknown"}
        ],
        "completed_steps": [
            {"id": "com_1", "step": "s"}
        ]
    }


def get_new_summary():
    return {
        "artifacts": [
            {"id": "art_2", "location": "path2", "type": "file", "value": "text2"}
        ],
        "observations": [
            {"id": "obs_2", "statement": "s2"}
        ],
        "understandings": [
            {"id": "und_2", "detail": "d2"}
        ],
        "hypotheses": [
            {"id": "hyp_2", "status": "unknown"}
        ],
        "completed_steps": [
            {"id": "com_2", "step": "s2"}
        ]
    }


def get_deltas():
    return DistillationDelta(
        artifacts=[
            ElementDelta(action=DeltaAction.REFINE, modifies_id="art_1", latest_id="art_2", text="refined", confidence=0.9)
        ],
        observations=[
            ElementDelta(action=DeltaAction.REPLACE, modifies_id="obs_1", latest_id="obs_2", text="new obs", confidence=0.8)
        ],
        understandings=[
            ElementDelta(action=DeltaAction.RESOLVE, modifies_id="und_1", latest_id="und_2", text="supported", confidence=0.95)
        ],
        hypotheses=[
            ElementDelta(action=DeltaAction.FLAG_CONFLICT, modifies_id="hyp_1", latest_id="hyp_2", text="conflict note", confidence=0.7)
        ],
        completed_steps=[
            ElementDelta(action=DeltaAction.RETIRE, modifies_id="com_1", latest_id="com_2", confidence=1.0)
        ]
    )


def test_apply_delta_extended():
    metrics = MetricsWrapper("test-worker-agent")
    agg = get_aggregate()
    new = get_new_summary()
    # add an unmentioned artifact to new summary
    new["artifacts"].append({"id": "art_3", "location": "path3", "type": "file", "value": "text3"})
    updated = apply_delta(metrics, agg, new, get_deltas())

    # artifacts
    art_ids = {a["id"] for a in updated["artifacts"]}
    assert "art_1" in art_ids
    assert "art_2" in art_ids
    assert "art_3" in art_ids
    # check refinement fields on art_1
    art1 = next(a for a in updated["artifacts"] if a["id"] == "art_1")
    assert art1.get("refinement") == "refined"
    assert art1.get("refinement_confidence") == 0.9

    # observations
    obs_ids = {o["id"] for o in updated["observations"]}
    # After REPLACE, the original id is overwritten by the new id
    assert "obs_2" in obs_ids
    assert "obs_1" not in obs_ids
    obs2 = next(o for o in updated["observations"] if o["id"] == "obs_2")
    assert obs2["statement"] == "s2"  # replaced

    # understandings
    und_ids = {u["id"] for u in updated["understandings"]}
    assert "und_1" in und_ids
    assert "und_2" in und_ids
    und1 = next(u for u in updated["understandings"] if u["id"] == "und_1")
    assert und1["status"] == "supported"
    assert und1["confidence"] == 0.95

    # hypotheses
    hyp_ids = {h["id"] for h in updated["hypotheses"]}
    assert "hyp_1" in hyp_ids
    assert "hyp_2" in hyp_ids
    assert "hyp_2_conflict_hyp_1" in hyp_ids
    hyp1 = next(h for h in updated["hypotheses"] if h["id"] == "hyp_1")
    assert hyp1.get("conflict_flag") is True

    # completed_steps should be empty after retire
    assert len(updated["completed_steps"]) == 0

    # unmentioned artifact art_3 should be present
    assert any(a["id"] == "art_3" for a in updated["artifacts"])

    # ensure no errors were printed (metrics may print but that's fine)
    print("test_apply_delta_extended passed")
