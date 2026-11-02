from typing import Dict, List, Any
from deepdiff import DeepDiff

def apply_delta_analysis(prior_aggregation: Dict[str, List[Dict]], delta_analysis: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Mechanically apply delta analysis to update prior aggregation.
    
    This function implements deterministic aggregation rules based on the
    delta analysis produced by the LLM. It ensures that the aggregation
    is consistent and repeatable.
    """
    # Start with a copy of the prior aggregation
    updated = {k: [dict(item) for item in v] for k, v in prior_aggregation.items()}
    
    # Helper to find item by content similarity
    def find_similar(items: List[Dict], target: Dict, key: str = "statement") -> List[int]:
        """Find indices of items similar to target"""
        similar = []
        target_content = target.get(key, "")
        for i, item in enumerate(items):
            if item.get(key, "") and target_content:
                # Simple similarity based on content
                if target_content.lower() in item.get(key, "").lower() or item.get(key, "").lower() in target_content.lower():
                    similar.append(i)
        return similar
    
    # Process each category
    for category in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        if category not in updated:
            updated[category] = []
        
        if category in delta_analysis:
            for delta_item in delta_analysis[category]:
                action = delta_item.get("action", "append")
                
                if action == "append":
                    # Remove action field before appending
                    clean_item = {k: v for k, v in delta_item.items() if k != "action"}
                    updated[category].append(clean_item)
                
                elif action == "update" or action == "update_status":
                    # Find similar items in prior aggregation
                    key = "statement" if category == "observations" else "hypothesis" if category == "hypotheses" else "concept" if category == "understandings" else "step" if category == "completed_steps" else "id"
                    similar_indices = find_similar(updated[category], delta_item, key)
                    
                    if similar_indices:
                        # Update the first similar item
                        idx = similar_indices[0]
                        if action == "update_status" and "status" in delta_item:
                            # Only update status field
                            updated[category][idx]["status"] = delta_item["status"]
                            if "confidence" in delta_item:
                                updated[category][idx]["confidence"] = delta_item["confidence"]
                        else:
                            # Update all fields except action
                            for k, v in delta_item.items():
                                if k != "action":
                                    updated[category][idx][k] = v
                    else:
                        # No similar item found, append instead
                        clean_item = {k: v for k, v in delta_item.items() if k != "action"}
                        updated[category].append(clean_item)
                
                elif action == "remove":
                    # Find and remove similar items
                    key = "statement" if category == "observations" else "hypothesis" if category == "hypotheses" else "concept" if category == "understandings" else "step" if category == "completed_steps" else "id"
                    similar_indices = find_similar(updated[category], delta_item, key)
                    
                    for idx in sorted(similar_indices, reverse=True):
                        if idx < len(updated[category]):
                            updated[category].pop(idx)
                
                elif action == "flag_conflict":
                    # Keep both, add a conflict flag to the new item
                    clean_item = {k: v for k, v in delta_item.items() if k != "action"}
                    clean_item["conflict_flagged"] = True
                    clean_item["conflict_reason"] = delta_item.get("conflict_reason", "Contradictory observation")
                    updated[category].append(clean_item)
    
    return updated

def merge_with_delta(prior_summary: List[Dict], delta_analysis: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Merge prior summary with delta analysis.
    
    This function handles the case where there might be multiple prior
    aggregations (from multiple compaction cycles).
    """
    # Start with the last aggregation as the base
    if not prior_summary:
        # No prior aggregation, just return the delta as new aggregation
        return {k: [dict(item) for item in v] if isinstance(v, list) else [v] for k, v in delta_analysis.items()}
    
    # Get the last aggregation
    last_aggregation = prior_summary[-1]
    
    # Apply delta to the last aggregation
    updated = apply_delta_analysis(last_aggregation, delta_analysis)
    
    return updated
