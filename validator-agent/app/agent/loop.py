from langchain_core.messages import SystemMessage, HumanMessage
from prompts.extraction import CLAIM_EXTRACTION_PROMPT
from prompts.validation import VALIDATION_PROMPT
from agent.telemetry import (
    promote_supporting_evidence,
    ingest_claims,
    fetch_evidence_events,
    link_claims_to_evidence,
    build_evidence_text,
)
from observability.metrics import MetricsWrapper
from typing import Dict
from langchain_ollama import ChatOllama

from contracts.validation_contracts.extraction import ExtractionResult
from contracts.validation_contracts.validation import ValidationResult


async def handle_claims_extraction(
    config: dict,
    metrics: MetricsWrapper,
    llm: ChatOllama,
    user_content: str,
    execution_id: str,
) -> ExtractionResult | None:
    """Extract discrete, checkable claims from an agent's final response.

    Mirrors the structured-output pattern used by ``extract_episode``: the LLM
    is wrapped with ``with_structured_output`` and the result is validated
    against the ``ExtractionResult`` contract.
    """
    operation_metric_labeler = metrics.get_counter_message_labeler("operation", "agent general activity")
    failure_metric_labeler = metrics.get_counter_message_labeler("error", "encountered error")

    metrics.emit(operation_metric_labeler({"operation" : "attempting claims extraction"}))
    messages = [SystemMessage(content=CLAIM_EXTRACTION_PROMPT), HumanMessage(content=user_content)]

    result = None
    last_error = None
    for _ in range(3):
        try:
            response = await llm.ainvoke(messages)
            if not isinstance(response, ExtractionResult):
                raise ValueError(f"expected an ExtractionResult object, got {type(response).__name__}")

            metrics.emit(operation_metric_labeler({"operation" : "claims extracted"}))
            return response
        except Exception as exc:
            metrics.emit(failure_metric_labeler({"failure" : "parsing error"}))
            last_error = str(exc)

    if result is None:
        metrics.emit(failure_metric_labeler({"failure" : "could not extract claims"}))
        print(f"Claims extraction failed after retries: {last_error}")

    return None


async def handle_validation(
    config: dict,
    metrics: MetricsWrapper,
    llm: ChatOllama,
    claims_map: dict,
    execution_id: str,
) -> Dict:
    """Rate each claim against a single evidence item.

    Returns ``{"support_map": ..., "overall_verdict": ...}`` to preserve the
    downstream contract.
    """
    support_metric_labeler = metrics.get_counter_message_labeler("support", "agent examined evidence")
    operation_metric_labeler = metrics.get_counter_message_labeler("operation", "agent general activity")
    failure_metric_labeler = metrics.get_counter_message_labeler("error", "encountered error")
    unexpected_claim_id_labeler = metrics.get_counter_message_labeler("failure", "unexpected claim id")

    is_supporting = {}
    claims_lookup = {}
    support_map = {}

    for c in claims_map['claims']:
        claims_lookup[c['claim_id']] = c

    try:
        events = await fetch_evidence_events(execution_id)
    except Exception as exc:
        return {"error": f"Failed to fetch evidence: {exc}"}

    validation_results = []

    for e in events:
        metrics.emit(operation_metric_labeler({"operation" : "iterate"}))
        evidence_text = await build_evidence_text(e)
        user_content = f"CLAIMS:\n{claims_map}\n\nEVIDENCE_ITEM:\n{evidence_text}"
        messages = [SystemMessage(content=VALIDATION_PROMPT), HumanMessage(content=user_content)]
        result = None
        last_error = None
        for _ in range(3):
            try:
                metrics.emit(operation_metric_labeler({"operation" : "invoke_attempt"}))
                response = await llm.ainvoke(messages)
                if not isinstance(response, ValidationResult):
                    raise ValueError(f"expected a ValidationResult object, got {type(response).__name__}")
                validation_results.append(response)
                break
            except Exception as exc:
                metrics.emit(failure_metric_labeler({"failure" : "parsing error"}))
                last_error = str(exc)
        if result is None:
            metrics.emit(failure_metric_labeler({"failure" : "gave up"}))
            result = {"error": f"Validation failed after retries: {last_error}"}

        vr = {"evidence_id" : e["evidence_id"], "result" : result}

        # add to support map in desired format
        evidence_id = vr.get("evidence_id")
        result = vr.get("result", {})
        support = result.get("support_map", {})

        for claim_id, support_obj in support.items():
            val = support_obj.get("supported", 0)
            if claim_id in claims_lookup:
                if claim_id not in support_map:
                    support_map[claim_id] = {}
                if val > 0:
                    is_supporting[evidence_id] = True
                    support_map[claim_id][evidence_id] = val
                    metrics.emit(support_metric_labeler({"support" : "supporting considered"}))
                else:
                    metrics.emit(support_metric_labeler({"support" : "un-supporting considered"}))
            else:
                metrics.emit(support_metric_labeler({"support" : "unknown claim id ref"}))

    #assert the LLM used the claim ids from the input list
    for claim_id in support_map.keys():
        if claim_id not in claims_lookup:
            metrics.emit(unexpected_claim_id_labeler({"failure" : "unexpected claim id"}))

    #ingest supporting evidence only once
    for id in is_supporting.keys():
        await promote_supporting_evidence(id)

    #use simple heuristic to determine overall support
    claim_scores = []
    for claim_id, evidence_vals in support_map.items():
        if evidence_vals:
            avg = sum(evidence_vals.values()) / len(evidence_vals)
            claim_scores.append(avg)
        else:
            claim_scores.append(0)
    overall = "unsupported"
    avg_overall = sum(claim_scores) / max(1, len(claim_scores))
    if avg_overall > 0.8:
        overall = "supported"
    elif avg_overall > 0.4:
        overall = "partially_supported"

    metrics.emit(support_metric_labeler({"support" : overall}))

    await link_claims_to_evidence(config, support_map)
    metrics.emit(operation_metric_labeler({"operation" : "linked"}))

    metrics.emit(operation_metric_labeler({"operation" : "completed"}))

    return {"support_map": support_map,
            "overall_verdict": overall}
