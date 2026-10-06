# compression.py
"""Compression utilities for the worker‑agent.

This module implements a *progressive* compression strategy that is
applicable to each iteration of the agent loop.  The compression is
deterministic, idempotent and never mutates the raw values stored in
``Iteration``.  The compressed representations are stored in the
``*_compressed`` fields and are used by :func:`derive_message_list`.

The design mirrors the sketch in the prompt but adds a per‑tool
compressor hook so that each tool can provide a custom strategy.
"""
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage

from observability.metrics import MetricsWrapper
from agent.models import Iteration
from toolbox.compressors import get_compressor

# ---------------------------------------------------------------------------
# Tiered compression limits
# ---------------------------------------------------------------------------
# (min_age, char_limit) – age 0 is the newest iteration.
# The tiers are intentionally simple; they can be tuned by the user.
TIERS: List[tuple[int, int]] = [(8, 600), (3, 3000), (0, None)]


def limit_for_age(age: int) -> Optional[int]:
    """Return the character limit for a given iteration age.

    The function walks the ``TIERS`` list in order and returns the first
    limit whose ``min_age`` is less than or equal to ``age``.
    """
    for min_age, limit in TIERS:
        if age >= min_age:
            return limit
    return None

# ---------------------------------------------------------------------------
# Helper: clip a string to a limit, keeping head and tail.
# ---------------------------------------------------------------------------

def clip_mid(metrics: MetricsWrapper, value: Any, limit: int) -> str:
    """Return a clipped representation of ``value``.

    The function keeps the first 70 % of the string as a *head* and the
    remainder as a *tail*.  The omitted portion is indicated with a
    ``...[N chars omitted]...`` marker.
    """
    s = value if isinstance(value, str) else str(value)
    if len(s) <= limit:
        return s
    head = int(limit * 0.7)
    tail = max(1, limit - head)
    omitted = len(s) - limit
    metrics.emit(metrics.get_counter_message("compression_amount", "reduced by this many chars", value=omitted))
    return f"{s[:head]}...[{omitted} chars omitted]...{s[-tail:]}"

# ---------------------------------------------------------------------------
# Compress an AIMessage – content and tool‑call arguments.
# ---------------------------------------------------------------------------

def compress_response(metrics: MetricsWrapper, resp: AIMessage, limit: int) -> AIMessage:
    """Return a compressed copy of ``resp``.

    The function keeps the same structure but clips the ``content`` and
    each tool‑call ``args`` using :func:`clip_mid`.
    """
    compressed_content = clip_mid(resp.content, limit) if resp.content else ""
    compressed_tool_calls = []
    for tc in resp.tool_calls or []:
        compressed_tool_calls.append(
            {
                "id": tc["id"],
                "name": tc["name"],
                "args": clip_mid(metrics, tc.get("args", {}), limit),
                "type": "tool_call",
            }
        )
    return AIMessage(content=compressed_content, tool_calls=compressed_tool_calls)

# ---------------------------------------------------------------------------
# Main compression routine
# ---------------------------------------------------------------------------

def compress_history(metrics: MetricsWrapper, history: List[Iteration], upto: int) -> int:
    """Compress the *raw* fields of ``history``.

    Parameters
    ----------
    history:
        The list of :class:`Iteration` objects.
    upto:
        Iterations with ``iteration <= upto`` are considered already
        folded into the summary and are skipped.

    Returns
    -------
    int
        The number of iterations that were (re)compressed.
    """
    if not history:
        return 0

    newest = history[-1].iteration
    changed = 0

    for it in history:
        if it.iteration <= upto:
            continue
        age = newest - it.iteration
        limit = limit_for_age(age)
        if limit is None or it.compression_limit == limit:
            continue

        # Re‑compress from the raw values – never mutate the originals.
        it.tool_call_result_compressed = get_compressor(it.tool_name)(it.tool_call_result)
        it.model_response_compressed = compress_response(metrics, it.model_response, limit)
        it.compression_limit = limit
        changed += 1

    return changed

# ---------------------------------------------------------------------------
# Expose a small helper for the loop to call.
# ---------------------------------------------------------------------------

def compress_and_log(metrics: MetricsWrapper, history: List[Iteration], upto: int):
    """Convenience wrapper that logs the number of compressed items.

    The function is intentionally thin – the heavy lifting is done by
    :func:`compress_history`.
    """
    changed = compress_history(metrics, history, upto)
    if changed:
        metrics.emit(metrics.get_counter_message("compression_changed", f"compressed iteration count", value=changed))
    return changed

# End of compression.py

