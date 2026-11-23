from typing import Dict, List, Any, Optional
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
from contracts.inference_contracts.agent_state_extended import (
    ExtendedAgentState,
    ExtendedAgentStateItem,
)

# Helper to find an item by ID within a specific section list
#use the item id prefix as a section name match
def _find_extended_item_by_id(aggregate: ExtendedAgentState, item_id: str) -> Optional[ExtendedAgentStateItem]:
    section_starts_with = item_id.split("_")[0]
    if item_id is not None:
        for section, items in aggregate.state_parts.items():
            if section.startswith(section_starts_with):
                for item in items:
                    if item.id == item_id:
                        return item
    return None
    
def apply_delta_to_aggregate(config: AgentRequest, 
                             metrics: MetricsWrapper,  
                             compact: Compaction, 
                             latest_extended_state: ExtendedAgentState, 
                             new_delta: DistillationDelta) -> ExtendedAgentState:
    #first lets add all items from the latest_extended_state to the aggregate
    aggregate = compact.aggregate
    for name, state_parts in latest_extended_state.state_parts.items():
        aggregated_parts = aggregate.state_parts.get(name, [])
        for item in state_parts:
            aggregated_parts.append(item)
        aggregate.state_parts[name] = aggregated_parts
        
    #now lets add the deltas
    for section, deltas in new_delta:
        for delta in deltas:
            target = _find_extended_item_by_id(aggregate, delta.modifies_id)
            if target is not None:
                target.deltas.append(delta)
    
    return aggregate
        
        
