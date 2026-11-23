from typing import Dict, List, TypeVar, Callable, Optional
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction
from pydantic import BaseModel
import json

T = TypeVar('T', bound=BaseModel)

# Define the signature for a per-type projection function
# Worker projection returns Optional[str] (markdown or None if retired)
WorkerProjectionFn = Callable[[ExtendedAgentStateItem[T]], Optional[str]]
# Delta projection returns Dict (scaffolding)
DeltaProjectionFn = Callable[[ExtendedAgentStateItem[T]], Dict]

# Placeholder type for specific projections
# In a real system, these would be imported from specific type files (e.g., hypothesis_projection.py)
# For now, we use a simple dictionary mapping
_PROJECTION_DISPATCHER: Dict[type, tuple[WorkerProjectionFn, DeltaProjectionFn]] = {}

def register_projection(item_type: type, worker_fn: WorkerProjectionFn, delta_fn: DeltaProjectionFn):
    """Registers a pair of projection functions for a specific item type T."""
    global _PROJECTION_DISPATCHER
    _PROJECTION_DISPATCHER[item_type] = (worker_fn, delta_fn)

def get_projection_functions(item_type: type) -> Optional[tuple[WorkerProjectionFn, DeltaProjectionFn]]:
    """Retrieves the registered projection functions for a given item type."""
    return _PROJECTION_DISPATCHER.get(item_type)


# --- State-level Traversal Functions ---

def project_for_worker(state: ExtendedAgentState) -> str:
    """
    Collects all non-None worker projections into a single markdown string.
    Never sends retired text.
    """
    worker_markdown_parts: List[str] = []
    
    for section_name, items in state.state_parts.items():
        for item in items:
            item_type = type(item.contains)
            
            projection_funcs = get_projection_functions(item_type)
            
            if projection_funcs:
                worker_fn, _ = projection_funcs
                
                # Per-type worker projection: ExtendedAgentStateItem[T] -> Optional[str]
                markdown_str = worker_fn(item)
                
                if markdown_str is not None:
                    worker_markdown_parts.append(markdown_str)
                    
    return "\n\n---\n\n".join(worker_markdown_parts)


def project_for_delta(state: ExtendedAgentState) -> Dict:
    """
    Generates a dictionary containing projections for delta extraction.
    Retired items are excluded, but the original state remains untouched.
    """
    delta_projections: Dict[str, Dict] = {} # Using section name as key
    
    for section_name, items in state.state_parts.items():
        section_deltas = {}
        for item in items:
            item_type = type(item.contains)
            
            projection_funcs = get_projection_functions(item_type)
            
            if projection_funcs:
                _, delta_fn = projection_funcs
                
                # Per-type delta extractor projection: (ExtendedAgentStateItem[T])-> Dict
                delta_dict = delta_fn(item)
                
                # Only include non-retired items in the delta projection
                is_retired = any(d.action == DeltaAction.RETIRE for d in item.deltas)
                if not is_retired:
                    # Use item ID for unique identification in the output dict
                    if item.id:
                        section_deltas[item.id] = delta_dict
                        
        if section_deltas:
            delta_projections[section_name] = section_deltas
            
    return delta_projections

from .Observation import project_for_worker as worker_proj_obs, project_for_delta as delta_proj_obs
from .Understanding import project_for_worker as worker_proj_und, project_for_delta as delta_proj_und
from .Hypothesis import project_for_worker as worker_proj_hyp, project_for_delta as delta_proj_hyp
from .CompletedStep import project_for_worker as worker_proj_completed_step, project_for_delta as delta_proj_completed_step
from .Artifact import project_for_worker as worker_proj_artifact, project_for_delta as delta_proj_artifact

# Register types
register_projection(type(Observation), worker_proj_obs, delta_proj_obs)
register_projection(type(Understanding), worker_proj_und, delta_proj_und)
register_projection(type(Hypothesis), worker_proj_hyp, delta_proj_hyp)
register_projection(type(CompletedStep), worker_proj_completed_step, delta_proj_completed_step)
register_projection(type(Artifact), worker_proj_artifact, delta_proj_artifact)
