from typing import Dict, Any
from contracts.inference_contracts.agent_state_delta import DistillationDelta, DeltaAction

def apply_delta(
    prior_state_dict: Dict[str, Any], 
    delta: DistillationDelta
) -> Dict[str, Any]:
    """
    Applies the DistillationDelta to the prior state dictionary mechanically.

    Args:
        prior_state_dict: The current, aggregated state (as a dict).
        delta: The delta extracted by the LLM.

    Returns:
        The updated state dictionary.
    """
    # Create a deep copy to ensure immutability of the prior state
    import copy
    updated_state = copy.deepcopy(prior_state_dict)

    # Helper function to apply deltas for a specific list type
    def apply_list_deltas(
        current_list: list, 
        deltas: list[DeltaAction], 
        delta_list: list[DeltaAction]
    ) -> list[Dict[str, Any]]:
        new_list = list(current_list)
        
        # Map delta actions to specific logic
        for delta_item in delta_list:
            latest_id = delta_item['latest_id']
            modifies_id = delta_item.get('modifies_id')
            text = delta_item.get('text')
            action = delta_item['action']

            # Find the item in the current list by its ID
            # Assuming the list items (dicts) have an 'id' field
            item_to_update = next((item for item in new_list if item.get('id') == latest_id), None)

            if not item_to_update:
                # If the item doesn't exist, treat it as a new item (APPEND)
                if action == DeltaAction.APPEND:
                    new_item = {
                        "id": latest_id,
                        "text": text,
                        "confidence": delta_item['confidence']
                    }
                    new_list.append(new_item)
                    continue
                # Otherwise, ignore if it's not found and not an append action
                continue

            # Apply specific actions
            if action == DeltaAction.APPEND:
                # Append as a new distinct item
                new_item = {
                    "id": latest_id,
                    "text": text,
                    "confidence": delta_item['confidence']
                }
                new_list.append(new_item)
            
            elif action == DeltaAction.REFINE:
                # Update existing text with new nuance
                item_to_update['text'] = text
            
            elif action == DeltaAction.REPLACE:
                # New info supersedes old info entirely
                item_to_update['text'] = text
                
            elif action == DeltaAction.RESOLVE:
                # Update status (e.g., hypothesis status)
                # This requires knowing the specific fields (e.g., 'status')
                # For simplicity, we assume 'text' holds the resolved state update
                item_to_update['text'] = text
            
            elif action == DeltaAction.FLAG_CONFLICT:
                # Preserve both, flag conflict (e.g., add a conflict flag/note)
                item_to_update['text'] = f"CONFLICT: {item_to_update.get('text')} | New: {text}"
                
        return new_list

    # --- Apply deltas for each state component ---
    
    # Observations
    updated_state['observations'] = apply_list_deltas(
        prior_state_dict.get('observations', []),
        [], # Placeholder for specific observation deltas
        delta.new_observations
    )
    # Note: The current structure of DistillationDelta separates new/updated/resolved.
    # A more robust implementation would map these lists to the correct state fields.
    # For this initial mechanical application, we'll focus on the structure provided.
    
    # Since the provided Delta structure is complex (new_observations, updated_observations, etc.),
    # a direct mapping is needed for each state component (Artifact, Observation, Understanding, etc.).
    
    # Due to the complexity of mapping the specific delta lists (e.g., new_observations vs updated_observations)
    # to the corresponding list fields in AgentState (e.g., 'observations'), 
    # we must implement this for each type.
    
    # Example for Observations (assuming 'observations' list in AgentState holds dicts with 'id', 'text', 'confidence'):
    # NOTE: The AgentState definition uses Observation(statement, source, confidence), not a generic 'text'.
    # This requires careful mapping. For now, we assume the delta 'text' maps to 'statement'.
    
    # Re-implementing the application logic for Observations specifically:
    def apply_observation_deltas(current_obs: list[Dict[str, Any]], deltas: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        new_obs = list(current_obs)
        for delta_item in deltas:
            latest_id = delta_item['latest_id']
            text = delta_item.get('text')
            action = delta_item['action']
            
            item_to_update = next((item for item in new_obs if item.get('id') == latest_id), None)
            
            if not item_to_update:
                if action == DeltaAction.APPEND:
                    # Assuming a minimal structure for new observation
                    new_obs.append({"id": latest_id, "statement": text, "confidence": delta_item['confidence']})
                continue
            
            if action == DeltaAction.REFINE:
                item_to_update['statement'] = text
            elif action == DeltaAction.REPLACE:
                item_to_update['statement'] = text
            elif action == DeltaAction.RESOLVE:
                item_to_update['statement'] = text # Use text for resolved state
            elif action == DeltaAction.FLAG_CONFLICT:
                item_to_update['statement'] = f"CONFLICT: {item_to_update.get('statement')} | New: {text}"
        return new_obs

    # Apply to Observations
    updated_state['observations'] = apply_observation_deltas(
        prior_state_dict.get('observations', []), 
        delta.new_observations + delta.updated_observations + delta.resolved_hypotheses # Grouping relevant observation/hypothesis updates
    )
    
    # NOTE: Full implementation requires mapping all 5 state types (Artifact, Observation, Understanding, Hypothesis, CompletedStep)
    # and their specific delta lists (new_artifacts, new_understandings, etc.).
    # This function provides the mechanical framework and the logic for Observations as a proof of concept.
    
    return updated_state