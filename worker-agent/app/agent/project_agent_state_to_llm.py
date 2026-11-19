from typing import Dict, List, Any, Optional
from copy import deepcopy

def project_for_llm(
    extended: AgentStateExtended,
    *,
    include_status: bool = True,
    include_confidence: bool = True,
    max_items_per_section: Optional[int] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Project AgentStateExtended -> LLM-visible AgentState dict.

    - Strips meta_entries entirely. LLM never sees clarifications, conflicts, retractions.
    - Deep-copies content so LLM / distillation code cannot mutate the persisted aggregate.
    - Does NOT include conflict_flag, refinement, note fields — those no longer exist in content.
    - Obsolete items are already removed from content by apply_delta, so they are not projected.
    - Returns a Dict[str, List[Dict]] in the exact shape your existing distillation prompt expects,
      so you can drop this in without changing the prompt.
    """
    content = deepcopy(extended.content)

    # Enforce the LLM-visible shape: only the 5 sections, no extra keys
    projected: Dict[str, List[Dict[str, Any]]] = {
        "artifacts": [],
        "observations": [],
        "understandings": [],
        "hypotheses": [],
        "completed_steps": [],
    }

    for section in projected.keys():
        items = content.get(section, [])
        # Optional: cap for context window — take most recent N, not arbitrary slice
        # If you cap, do it here, not in apply_delta, so the aggregate stays complete
        if max_items_per_section is not None and len(items) > max_items_per_section:
            items = items[-max_items_per_section:]

        for item in items:
            # Build a clean LLM-visible copy — whitelist fields, don't pass through dict as-is
            # This is the enforcement point: even if content somehow has a stray field,
            # it will not leak to the LLM.
            clean: Dict[str, Any] = {
                "id": item.get("id"),
                "text": item.get("text", ""),
            }
            if include_confidence and "confidence" in item:
                clean["confidence"] = item.get("confidence")
            # status is content for hypotheses (RESOLVE) — keep it for LLM, it's not meta
            if include_status and section == "hypotheses" and "status" in item:
                clean["status"] = item.get("status")
            # completed_steps are often just strings in your old code — handle both shapes
            if section == "completed_steps" and isinstance(item, str):
                clean = {"id": item, "text": item}  # type: ignore

            projected[section].append(clean)

    return projected

def project_for_llm_with_conflict_summary(
    extended: AgentStateExtended,
    *,
    max_conflicts: int = 5,
) -> Dict[str, Any]:
    """
    Optional variant: if you DO want the LLM to know about conflicts,
    don't give it raw meta_entries. Give it a summarized, read-only view.

    This is the compromise if you find distillation stalls because it
    keeps re-proposing conflicting understandings without knowing they conflict.

    The LLM sees:
    - content (as above)
    - conflict_summaries: list of {target_id, text} — no full meta, no provenance

    It does NOT see provenance, refine history, retractions, or superseded text.
    It cannot write to meta. It can only emit FLAG_CONFLICT again, which fold will dedupe.
    """
    base = project_for_llm(extended)

    conflicts = [
        {"target_id": m.target_id, "text": m.text}
        for m in extended.meta_entries
        if m.type == "conflict"
    ][-max_conflicts:]

    return {
        **base,
        # Keep this key separate from content sections so your existing prompt
        # that iterates sections won't mistake it for a new section.
        "_conflict_summaries": conflicts,
    }
