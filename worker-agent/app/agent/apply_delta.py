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

def apply_delta(
    metrics: MetricsWrapper,
    extended: AgentStateExtended,
    new_summary: Dict[str, List[Dict[str, Any]]],
    deltas: DistillationDelta,
) -> AgentStateExtended:
    """
    Mechanically applies state deltas to the extended agent state.

    Rules:
    - Content holds only LLM-visible items. No refinement/note/conflict_flag fields.
    - Meta holds all provenance / clarification / conflict / retraction records.
    - FLAG_CONFLICT is meta-only. No fake items appended to content.
    - obsolete_context removes from content but records a retraction in meta.
    """
    content = extended.content

    for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        handled_ids: set[str] = set()

        for delta in getattr(deltas, section, []):
            try:
                target_item = _find_item(content, section, delta.modifies_id)
                source_item = _find_item(new_summary, section, delta.latest_id)
                if delta.latest_id:
                    handled_ids.add(delta.latest_id)

                # Target for meta is modifies_id if present, else latest_id (APPEND case)
                meta_target = delta.modifies_id or delta.latest_id

                if delta.action == DeltaAction.APPEND:
                    metrics.emit(metrics.get_counter_message("distillation_delta_appends", "distillation delta agent updates context"))
                    # Fix for old bug: always append, whether source exists or we construct from delta.text
                    if source_item is None:
                        # Construct from delta.text — explicit, not fallthrough
                        new_item = {
                            "id": delta.latest_id,
                            "text": delta.text or "",
                            "confidence": delta.confidence,
                        }
                        content[section].append(new_item)
                    else:
                        # Avoid duplicate append if already in aggregate (old code could double-append)
                        if _find_item(content, section, source_item.get("id")) is None:
                            content[section].append(source_item)
                    extended.meta_entries.append(_make_meta(
                        type_="provenance",
                        target_id=meta_target,
                        source_id=delta.latest_id,
                        section=section,
                        text=f"Appended: {delta.text or ''}",
                        confidence=delta.confidence,
                        action=delta.action,
                    ))

                elif delta.action == DeltaAction.REFINE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_refined_{section}", "distillation delta agent updates context"))
                    if target_item:
                        old_text = target_item.get("text", "")
                        # REFINE = rewrite content, not add refinement field, not append duplicate
                        new_text = delta.text
                        if new_text is None and source_item is not None:
                            new_text = source_item.get("text", "")
                        if new_text is not None:
                            target_item["text"] = new_text
                        if source_item is not None:
                            # Update confidence from source, but keep old in meta
                            target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="refine",
                            target_id=meta_target,
                            source_id=delta.latest_id,
                            section=section,
                            text=f"Refined: {old_text} -> {new_text}. Reason: {delta.text or ''}",
                            confidence=delta.confidence,
                            action=delta.action,
                        ))

                elif delta.action == DeltaAction.REPLACE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_replaced_{section}", "distillation delta agent updates context"))
                    if target_item and source_item:
                        # Overwrite content with source, record supersession in meta, not note field
                        old_text = target_item.get("text", "")
                        for k, v in source_item.items():
                            target_item[k] = v
                        extended.meta_entries.append(_make_meta(
                            type_="superseded",
                            target_id=meta_target,
                            source_id=delta.latest_id,
                            section=section,
                            text=f"Replaced: {old_text} -> {source_item.get('text','')}. Reason: {delta.text or ''}",
                            confidence=delta.confidence,
                            action=delta.action,
                        ))
                    elif target_item and delta.text:
                        # No source_item, use delta.text as new content
                        old_text = target_item.get("text", "")
                        target_item["text"] = delta.text
                        target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="superseded",
                            target_id=meta_target,
                            source_id=delta.latest_id,
                            section=section,
                            text=f"Replaced (from delta.text): {old_text} -> {delta.text}",
                            confidence=delta.confidence,
                            action=delta.action,
                        ))

                elif delta.action == DeltaAction.RESOLVE:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_resolved_{section}", "distillation delta agent updates context"))
                    if target_item:
                        old_status = target_item.get("status", "")
                        old_conf = target_item.get("confidence")
                        # RESOLVE is a content change for hypotheses: status is content
                        target_item["status"] = delta.text or ""
                        target_item["confidence"] = delta.confidence
                        extended.meta_entries.append(_make_meta(
                            type_="resolve",
                            target_id=meta_target,
                            source_id=delta.latest_id,
                            section=section,
                            text=f"Resolved: status {old_status} ({old_conf}) -> {delta.text}. Source: {delta.latest_id}",
                            confidence=delta.confidence,
                            action=delta.action,
                        ))

                elif delta.action == DeltaAction.FLAG_CONFLICT:
                    metrics.emit(metrics.get_counter_message(f"distillation_delta_flagged_conflicting_{section}", "distillation delta agent updates context"))
                    # META-ONLY. No conflict_flag field. No fake *_conflict item.
                    # This stops the feedback loop where conflict notes get re-distilled as observations.
                    if target_item or delta.modifies_id:
                        extended.meta_entries.append(_make_meta(
                            type_="conflict",
                            target_id=meta_target,
                            source_id=delta.latest_id,
                            section=section,
                            text=delta.text or "Conflict detected",
                            confidence=delta.confidence,
                            action=delta.action,
                        ))
                    # Do NOT append source_item here as a new observation — it is already in new_summary
                    # and will be handled by the unmentioned-items pass below if needed.

            except Exception as e:
                print(f"Error applying delta {delta}: {e}")
                continue

        # Unmentioned items from new_summary: items the LLM didn't emit a delta for
        # These are genuine new items, not conflicts. Append them, record provenance.
        if section in new_summary:
            for item in new_summary[section]:
                item_id = item.get("id")
                if item_id and item_id not in handled_ids:
                    if _find_item(content, section, item_id) is None:
                        metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_added_unmentioned", "distillation delta agent did not mention item"))
                        content[section].append(item)
                        extended.meta_entries.append(_make_meta(
                            type_="provenance",
                            target_id=item_id,
                            source_id=item_id,
                            section=section,
                            text="Added unmentioned from new_summary",
                            confidence=item.get("confidence", 0.5),
                            action=DeltaAction.APPEND,
                        ))

    # obsolete_context: remove from content, but keep a tombstone in meta
    if deltas.obsolete_context:
        # Note: your old code had a bug here — it looped sections but used a single remove_index
        # and only removed one item per section. This version removes all obsolete ids across all sections.
        for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
            to_remove = []
            for idx, item in enumerate(content.get(section, [])):
                if item.get("id") in deltas.obsolete_context:
                    to_remove.append(idx)
            # Remove in reverse to keep indices valid
            for idx in reversed(to_remove):
                removed = content[section].pop(idx)
                metrics.emit(metrics.get_counter_message(f"distillation_delta_{section}_cleaned_obsolete", "distillation delta agent cleaned up context"))
                extended.meta_entries.append(_make_meta(
                    type_="retraction",
                    target_id=removed.get("id", ""),
                    source_id=removed.get("id", ""),
                    section=section,
                    text=f"Marked obsolete: {removed.get('text','')[:200]}",
                    confidence=0.9,
                    action=DeltaAction.REPLACE,  # obsolete is a replacement by absence
                ))

    return extended
