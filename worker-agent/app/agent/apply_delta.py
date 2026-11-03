from typing import Dict, List, Any
from contracts.inference_contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction

def apply_delta(
    summary_aggregate: Dict[str, List[Dict[str, Any]]], 
    summary_ids: List[Dict[str, str]], 
    deltas: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mechanically applies state deltas to the aggregated agent state dictionary.

    Args:
        summary_aggregate: The current aggregated state (dict representation).
        summary_ids: List of IDs and their sections (e.g., [{"id": "art_2_0", "section": "artifacts"}]).
        deltas: List of ElementDelta dicts describing changes.

    Returns:
        The updated aggregated state dictionary.
    """
    # Deep copy the aggregate state to ensure immutability during processing
    updated_state = {k: list(v) for k, v in summary_aggregate.items()}

    # Helper to find an item by ID within a specific section list
    def find_item_by_id(section: str, item_id: str) -> Optional[Dict[str, Any]]:
        if section in updated_state:
            for item in updated_state[section]:
                if item.get("id") == item_id:
                    return item
        return None

    # Process each delta
    for delta_dict in deltas:
        try:
            # Convert delta dict to ElementDelta for type safety and access
            delta = ElementDelta(**delta_dict)
            section = delta.section # Assuming 'section' is available in the delta dict/model
            
            # 1. Identify the target item in the current state
            target_item = find_item_by_id(section, delta.modifies_id)
            
            # 2. Apply reconciliation logic based on DeltaAction
            if delta.action == DeltaAction.APPEND:
                # New observation/understanding/artifact -> Append
                # Note: We need to construct the full item based on delta.text/data
                # For simplicity here, we assume delta.text contains the necessary data for a new item
                new_item = {"id": delta.latest_id, "text": delta.text, "confidence": delta.confidence} # Simplified structure
                updated_state[section].append(new_item)
            
            elif delta.action == DeltaAction.REFINE:
                # Existing understanding refined -> Update status, retain history
                if target_item:
                    target_item.update({"text": delta.text, "confidence": delta.confidence})
            
            elif delta.action == DeltaAction.REPLACE:
                # New info supersedes old info entirely
                if target_item:
                    target_item.update({"text": delta.text, "confidence": delta.confidence})
            
            elif delta.action == DeltaAction.RESOLVE:
                # Hypothesis confirmed/rejected -> Update status, retain history
                if target_item:
                    # Assuming the item has a 'status' field for hypotheses
                    target_item['status'] = delta.text # Use text to convey status (e.g., "supported")
                    target_item['confidence'] = delta.confidence
            
            elif delta.action == DeltaAction.FLAG_CONFLICT:
                # Contradictory observation -> Preserve both, flag conflict
                # This requires a more complex structure (e.g., adding a 'conflict_flag' field)
                if target_item:
                    target_item['conflict_flag'] = True
                    # Optionally append a conflict note
                    updated_state[section].append({"id": f"{delta.latest_id}_conflict", "text": f"Conflict detected for {delta.latest_id}", "confidence": delta.confidence})

        except Exception as e:
            print(f"Error applying delta {delta_dict}: {e}")
            # Log error but continue processing other deltas

    return updated_state

# Example usage (for testing):
# summary_aggregate_example = {"observations": [{"id": "obs_2_0", "statement": "old"}, {"id": "obs_2_1", "statement": "old"}], "hypotheses": [{"id": "hyp_2_0", "hypothesis": "pending"}]}
# summary_example = [{"id": "art_2_0", "section": "artifacts"}, {"id": "obs_2_0", "section": "observations"}, {"id": "obs_2_1", "section": "observations"}, {"id": "hyp_2_0", "section": "hypotheses"}]
# delta_example = [{"latest_id": "art_2_0", "modifies_id": None, "text": "new artifact text", "confidence": 1.0, "action": "append", "section": "artifacts"}]
# updated_state = apply_delta(summary_aggregate_example, summary_example, [delta_example])
# import json
# print(json.dumps(updated_state, indent=2))