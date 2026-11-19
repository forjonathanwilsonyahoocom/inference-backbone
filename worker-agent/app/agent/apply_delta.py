from typing import Dict, List, Any, Optional
from contracts.inference_contracts.projected_agent_state import AgentStateExtended, MetaEntry
from contracts.inference_contracts.agent_state_delta import ElementDelta, DeltaAction, DistillationDelta
from observability.metrics import MetricsWrapper
import uuid

def _find_item(state_content: Dict[str, List[Dict[str, Any]]], section: str, item_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not item_id or section not in state_content:
        return None
    for item in state_content[section]:
        if item.get("id") == item_id:
            return item
    return None

def _make_meta(
    type_: str,
    target_id: str,
    source_id: str,
    section: str,
    text: str,
    confidence: float,
    action: DeltaAction,
) -> MetaEntry:
    return MetaEntry(
        id=str(uuid.uuid4()),
        type=type_,  # type: ignore
        target_id=target_id,
        source_id=source_id,
        target_type=section,
        text=text,
        confidence=confidence,
        source_delta_action=action.value,
    )
    
def _validate_deltas(
    extended: AgentStateExtended,
    new_summary: Dict[str, List[Dict[str, Any]]],
    deltas: DistillationDelta,
) -> None:
    """GPT's invariant: every reference must resolve before we mutate anything."""
    for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        for delta in getattr(deltas, section, []):
            # latest_id must always resolve in new_summary, except APPEND-from-text case
            # where delta.text provides content and source may not exist.
            # We still require it for REFINE/REPLACE/RESOLVE/FLAG_CONFLICT.
            if delta.action in (DeltaAction.REFINE, DeltaAction.REPLACE, DeltaAction.RESOLVE, DeltaAction.FLAG_CONFLICT):
                if _find_item(new_summary, section, delta.latest_id) is None:
                    raise ValueError(f"{section} delta {delta.latest_id}: latest_id not found in new_summary")
            # modifies_id must resolve if present
            if delta.modifies_id is not None:
                if _find_item(extended.content, section, delta.modifies_id) is None:
                    raise ValueError(f"{section} delta: modifies_id {delta.modifies_id} not found in prior aggregate")
            # APPEND must NOT have modifies_id
            if delta.action == DeltaAction.APPEND and delta.modifies_id is not None:
                raise ValueError(f"{section} APPEND delta should not have modifies_id, got {delta.modifies_id}")

def _normalize_completed_steps(content: Dict[str, List[Dict[str, Any]]]) -> None:
    """GPT P2: normalize completed_steps to dicts on entry, don't support both shapes everywhere."""
    normalized = []
    for item in content.get("completed_steps", []):
        if isinstance(item, str):
            normalized.append({"id": item, "text": item, "confidence": 1.0})
        else:
            normalized.append(item)
    content["completed_steps"] = normalized

def apply_delta_v2(
    metrics: MetricsWrapper,
    extended: AgentStateExtended,
    new_summary: Dict[str, List[Dict[str, Any]]],
    deltas: DistillationDelta,
) -> AgentStateExtended:
    # 1. Normalize once, up front
    _normalize_completed_steps(extended.content)
    _normalize_completed_steps(new_summary)

    # 2. Validate all references BEFORE mutating — no partial application
    _validate_deltas(extended, new_summary, deltas)

    content = extended.content

    for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        handled_ids: set[str] = set()

        for delta in getattr(deltas, section, []):
            try:
                target_item = _find_item(content, section, delta.modifies_id)
                source_item = _find_item(new_summary, section, delta.latest_id)
                meta_target = delta.modifies_id or delta.latest_id

                if delta.action == DeltaAction.APPEND:
                    metrics.emit(metrics.get_counter_message("distillation_delta_appends", "distillation delta agent updates context"))
                    if source_item is None:
                        new_item = {"id": delta.latest_id, "text": delta.text or "", "confidence": delta.confidence}
                        content[section].append(new_item)
                    else:
                        if _find_item(content, section, source_item.get("id")) is None:
                            content[section].append(source_item)
                    extended.meta_entries.append(_make_meta(
                        type_="provenance", target_id=meta_target, source_id=delta.latest_id,
                        section=section, text=f"Appended: {delta.text or ''}",
                        confidence=delta.confidence, action=delta.action,
                    ))
                    # FIX: only mark handled AFTER success
                    handled_ids.add(delta.latest_id)

                elif delta.action == DeltaAction.REFINE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_refined_{section}", "distillation delta agent updates context"))
                    if target_item:
                        old_text = target_item.get("text", "")
                        new_text = delta.text if delta.text is not None else (source_item.get("text", "") if source_item else "")
                        target_item["text"] = new_text
                        target_item["confidence"] = delta.confidence
                        # Identity preserved: target keeps modifies_id, never takes source id
                        extended.meta_entries.append(_make_meta(
                            type_="refine", target_id=meta_target, source_id=delta.latest_id,
                            section=section, text=f"Refined: {old_text} -> {new_text}",
                            confidence=delta.confidence, action=delta.action,
                        ))
                    handled_ids.add(delta.latest_id)

                elif delta.action == DeltaAction.REPLACE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_replaced_{section}", "distillation delta agent updates context"))
                    # FIX: REPLACE identity — do NOT copy source id into target
                    # Target keeps its own id (modifies_id). Source keeps its own id (latest_id).
                    # We supersede content, not identity.
                    if target_item and source_item:
                        old_text = target_item.get("text", "")
                        # Copy all fields EXCEPT id — preserve target identity
                        for k, v in source_item.items():
                            if k != "id":
                                target_item[k] = v
                        target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="superseded", target_id=meta_target, source_id=delta.latest_id,
                            section=section, text=f"Superseded: {old_text} -> {source_item.get('text','')}. Reason: {delta.text or ''}",
                            confidence=delta.confidence, action=delta.action,
                        ))
                    elif target_item and delta.text:
                        old_text = target_item.get("text", "")
                        target_item["text"] = delta.text
                        target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="superseded", target_id=meta_target, source_id=delta.latest_id,
                            section=section, text=f"Superseded (from delta.text): {old_text} -> {delta.text}",
                            confidence=delta.confidence, action=delta.action,
                        ))
                    handled_ids.add(delta.latest_id)

                elif delta.action == DeltaAction.RESOLVE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_resolved_{section}", "distillation delta agent updates context"))
                    if target_item:
                        old_status = target_item.get("status", "")
                        target_item["status"] = delta.text or ""
                        target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="resolve", target_id=meta_target, source_id=delta.latest_id,
                            section=section, text=f"Resolved: {old_status} -> {delta.text}",
                            confidence=delta.confidence, action=delta.action,
                        ))
                    handled_ids.add(delta.latest_id)

                elif delta.action == DeltaAction.FLAG_CONFLICT:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_flagged_conflicting_{section}", "distillation delta agent updates context"))
                    # Meta-only, no fake item, no conflict_flag
                    extended.meta_entries.append(_make_meta(
                        type_="conflict", target_id=meta_target, source_id=delta.latest_id,
                        section=section, text=delta.text or "Conflict detected",
                        confidence=delta.confidence, action=delta.action,
                    ))
                    handled_ids.add(delta.latest_id)

            except Exception as e:
                # FIX: durable failure record, not just print
                # Do NOT add to handled_ids on failure — unmentioned pass can still pick it up
                # or next distillation can retry it. We record the failure.
                print(f"Error applying delta {delta}: {e}")
                extended.meta_entries.append(_make_meta(
                    type_="annotation", target_id=delta.modifies_id or delta.latest_id,
                    source_id=delta.latest_id, section=section,
                    text=f"Failed to apply delta {delta.action.value}: {e}",
                    confidence=delta.confidence, action=delta.action,
                ))
                continue

        # Unmentioned pass — unchanged, but now handled_ids is only successes
        if section in new_summary:
            for item in new_summary[section]:
                item_id = item.get("id")
                if item_id and item_id not in handled_ids:
                    if _find_item(content, section, item_id) is None:
                        metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_added_unmentioned", "distillation delta agent did not mention item"))
                        content[section].append(item)
                        extended.meta_entries.append(_make_meta(
                            type_="provenance", target_id=item_id, source_id=item_id,
                            section=section, text="Added unmentioned from new_summary",
                            confidence=item.get("confidence", 0.5), action=DeltaAction.APPEND,
                        ))

    # obsolete_context — same as v1, but with validation that IDs exist
    if deltas.obsolete_context:
        for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
            to_remove = [idx for idx, item in enumerate(content.get(section, [])) if item.get("id") in deltas.obsolete_context]
            for idx in reversed(to_remove):
                removed = content[section].pop(idx)
                metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_cleaned_obsolete", "distillation delta agent cleaned up context"))
                extended.meta_entries.append(_make_meta(
                    type_="retraction", target_id=removed.get("id", ""), source_id=removed.get("id", ""),
                    section=section, text=f"Marked obsolete: {removed.get('text','')[:200]}",
                    confidence=0.9, action=DeltaAction.REPLACE,
                ))

    return extended
