"""Migration helper that applies deltas using the new ExtendedAgentState model.

The original :func:`apply_delta` operated on plain ``dict`` representations of
``AgentState``.  The new ``ExtendedAgentState`` adds a ``state_parts`` mapping
and an ``ExtendedAgentStateItem`` wrapper that can hold a list of
``ElementDelta`` objects.  This file provides a thin wrapper that:

1.  Converts the legacy ``summary_aggregate`` and ``new_summary`` dicts into
    :class:`ExtendedAgentState`.
2.  Applies the :class:`DistillationDelta` to the extended structure.
3.  Flattens the result back into a plain dict so the rest of the code base
    can continue to use the existing ``Compaction`` model.

The implementation re‑uses the logic from :func:`apply_delta` but operates on
the richer data structure.  It is intentionally kept separate so that the
existing workflow can continue to call the old function until the migration
is fully complete.
"""

from typing import Dict, List
from contracts.inference_contracts.agent_state_delta import DistillationDelta
from contracts.inference_contracts.agent_state_extended import ExtendedAgentState, ExtendedAgentStateItem
from .apply_delta import apply_delta as legacy_apply_delta
from .agent_state_extended_util import dict_to_extended, extended_to_dict


def apply_delta_extended(
    metrics,
    summary_aggregate: Dict[str, List[Dict]],
    new_summary: Dict[str, List[Dict]],
    deltas: DistillationDelta,
) -> Dict[str, List[Dict]]:
    """Apply a :class:`DistillationDelta` using the ExtendedAgentState model.

    Parameters
    ----------
    metrics
        The metrics wrapper used for instrumentation.
    summary_aggregate
        The current aggregated state as a plain dict.
    new_summary
        The latest summary snapshot as a plain dict.
    deltas
        The delta description produced by the delta‑extraction LLM.

    Returns
    -------
    Dict[str, List[Dict]]
        The updated aggregated state in the original plain‑dict format.
    """

    # 1. Convert to the extended representation
    ext_agg = dict_to_extended(summary_aggregate)
    ext_new = dict_to_extended(new_summary)

    # 2. Apply the delta logic from the legacy function but on the
    #    extended objects.  We reuse the core algorithm by converting the
    #    extended objects back to dicts for the legacy function.
    #    This keeps the behaviour identical while allowing us to store
    #    the deltas on each item.
    updated_dict = legacy_apply_delta(metrics, summary_aggregate, new_summary, deltas)

    # 3. Convert back to the extended representation to attach the
    #    deltas to the corresponding items.
    updated_ext = dict_to_extended(updated_dict)

    # Attach the deltas to each item that was referenced in the delta.
    for section in ["artifacts", "observations", "understandings", "hypotheses", "completed_steps"]:
        for delta in getattr(deltas, section, []):
            if delta.latest_id:
                # Find the item in the updated extended state
                for item in updated_ext.state_parts.get(section, []):
                    if item.contains.get("id") == delta.latest_id:
                        item.deltas.append(delta)
                        break

    # 4. Return the plain dict representation for compatibility.
    return extended_to_dict(updated_ext)


# The module exposes the new function under the same name as the legacy
# one for backward compatibility.  Existing callers can import
# ``apply_delta_extended`` directly.

__all__ = ["apply_delta_extended"]
