from typing import Dict, List, Any, Optional
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper

# Helper to find an item by ID within a specific section list
def find_item_by_id(state_representation: Dict[str, List[Dict[str, Any]]], section: str, item_id: str) -> Optional[Dict[str, Any]]:
    if section in state_representation and item_id:
        for item in state_representation[section]:
            if item.get("id") == item_id:
                return item
    return None
        
def apply_delta(
    metrics: MetricsWrapper,
    summary_aggregate: Dict[str, List[Dict[str, Any]]], 
    new_summary: Dict[str, List[Dict[str, Any]]], 
    deltas: DistillationDelta
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mechanically applies state deltas to the aggregated agent state dictionary.

    Args:
        summary_aggregate: The current aggregated state (dict representation).
        new_summary: latest dict representation of agent state with ids appended
        deltas: DistillationDelta describing changes.

    Returns:
        The updated aggregated state dictionary.
    """

    for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        # 1. Handle RETIRE actions first
        retire_deltas = [d for d in getattr(deltas, section, []) if d.action == DeltaAction.RETIRE]
        for d in retire_deltas:
            try:
                target_item = find_item_by_id(summary_aggregate, section, d.modifies_id)
                source_item = find_item_by_id(new_summary, section, d.latest_id)
                metrics.emit(metrics.get_counter_message("distillation_delta_retired", "distillation delta agent retires context"))
                if target_item:
                    summary_aggregate[section].remove(target_item)
                if source_item and source_item in summary_aggregate[section]:
                    summary_aggregate[section].remove(source_item)
                handled_ids.add(d.latest_id or d.modifies_id)
            except Exception as e:
                print(f"Error applying retire delta {d}: {e}")
        # 2. Process remaining actions
        for delta in getattr(deltas, section, []):
            if delta.action == DeltaAction.RETIRE:
                continue  # already handled
            try:
                target_item = find_item_by_id(summary_aggregate, section, delta.modifies_id)
                source_item = find_item_by_id(new_summary, section, delta.latest_id)
                if delta.latest_id:
                    handled_ids.add(delta.latest_id)
                if delta.action == DeltaAction.APPEND:
                    metrics.emit(metrics.get_counter_message("distillation_delta_appends", "distillation delta agent updates context"))
                    if source_item is None:
                        source_item = {"id": delta.latest_id, "text": delta.text, "confidence": delta.confidence}
                    else:
                        summary_aggregate[section].append(source_item)
                elif delta.action == DeltaAction.REFINE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_refined_{section}", "distillation delta agent updates context"))
                    if target_item:
                        target_item.update({"refinement": delta.text, "refinement_confidence": delta.confidence})
                    if source_item:
                        summary_aggregate[section].append(source_item)
                elif delta.action == DeltaAction.REPLACE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_replaced_{section}", "distillation delta agent updates context"))
                    if target_item and source_item:
                        for k, v in source_item.items():
                            target_item.update({k: v})
                    if target_item and delta.text:
                        target_item.update({"note": delta.text, "note_confidence": delta.confidence})
                elif delta.action == DeltaAction.RESOLVE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_resolved_{section}", "distillation delta agent updates context"))
                    if target_item:
                        target_item['status'] = delta.text
                        target_item['confidence'] = delta.confidence
                    if source_item:
                        summary_aggregate[section].append(source_item)
            except Exception as e:
                print(f"Error applying delta {delta}: {e}")

        
        if section in new_summary:
            for item in new_summary[section]:
                if item["id"] not in handled_ids:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_added_unmentioned", "distillation delta agent did not mention item"))
                    summary_aggregate[section].append(item)
                    
        
# obsolete_context handling removed

print(summary_aggregate)
return summary_aggregate

