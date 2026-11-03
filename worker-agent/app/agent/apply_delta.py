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
        # Process each delta
        handled_ids = set()
        for delta in getattr(deltas, section, []):
            try:                
                # 1. Identify the target item in the current state
                target_item = find_item_by_id(summary_aggregate, section, delta.modifies_id)
                source_item = find_item_by_id(new_summary, section, delta.latest_id)
                if delta.latest_id:
                    handled_ids.add(delta.latest_id)
                # 2. Apply reconciliation logic based on DeltaAction
                if delta.action == DeltaAction.APPEND:
                    # New observation/understanding/artifact -> Append
                    metrics.emit(metrics.get_counter_message("distillation_delta_appends", "distillation delta agent updates context"))
                    if source_item is None:
                        # Note: We need to construct the full item based on delta.text/data
                        # For simplicity here, we assume delta.text contains the necessary data for a new item
                        source_item = {"id": delta.latest_id, "text": delta.text, "confidence": delta.confidence}
                    else:
                        summary_aggregate[section].append(source_item)
                
                elif delta.action == DeltaAction.REFINE:
                    # Existing understanding refined -> Update status, retain history
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_refined_{section}", "distillation delta agent updates context"))
                    if target_item:
                        target_item.update({"refinement": delta.text, "refinement_confidence": delta.confidence})
                    if source_item:
                        summary_aggregate[section].append(source_item)
                
                elif delta.action == DeltaAction.REPLACE:
                    # New info supersedes old info entirely
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_replaced_{section}", "distillation delta agent updates context"))
                    if target_item and source_item:
                        for k,v in source_item.items():
                            target_item.update({k : v})
                    if target_item and delta.text:
                        target_item.update({"note": delta.text, "note_confidence": delta.confidence})
                
                elif delta.action == DeltaAction.RESOLVE:
                    # Hypothesis confirmed/rejected -> Update status, retain history
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_resolved_{section}", "distillation delta agent updates context"))
                    if target_item:
                        # Assuming the item has a 'status' field for hypotheses
                        target_item['status'] = delta.text # Use text to convey status (e.g., "supported")
                        target_item['confidence'] = delta.confidence
                    if source_item:
                        summary_aggregate[section].append(source_item)
                        
                elif delta.action == DeltaAction.FLAG_CONFLICT:
                    # Contradictory observation -> Preserve both, flag conflict
                    # This requires a more complex structure (e.g., adding a 'conflict_flag' field)
                    
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_flagged_conflicting_{section}", "distillation delta agent updates context"))
                    if target_item:
                        target_item['conflict_flag'] = True
                        # Optionally append a conflict note
                        t = delta.text if delta.text else ""
                        s = f"_{delta.modifies_id}" if delta.modifies_id else ""
                        summary_aggregate[section].append({"id": f"{delta.latest_id}_conflict{s}", "text": f"Conflict detected {t}", "confidence": delta.confidence})
                    if source_item:
                        summary_aggregate[section].append(source_item)
            except Exception as e:
                print(f"Error applying delta {delta}: {e}")
                # Log error but continue processing other deltas
        
        if section in new_summary:
            for item in new_summary[section]:
                if item["id"] not in handled_ids:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_added_unmentioned", "distillation delta agent did not mention item"))
                    summary_aggregate[section].append(item)
                    
        remove_index = -1
        if deltas.obsolete_context:
            for identifier in deltas.obsolete_context:
                for index, item in enumerate(summary_aggregate[section]):
                    if item["id"] == identifier:
                        metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_cleaned_obsolete", "distillation delta agent cleaned up context"))
                        remove_index = index
                        break
            if remove_index >= 0:
                del summary_aggregate[section][remove_index]
                
    print(summary_aggregate)
    return summary_aggregate

