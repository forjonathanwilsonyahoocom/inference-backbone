import json
import os
import uuid
from observability.metrics import MetricsWrapper
import hashlib
from typing import Any, List, Optional, Dict
from pydantic import BaseModel
from ollama import ResponseError 


from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)

from langchain_ollama import ChatOllama
from langchain_core.tools import tool

from prompts.distillation import DISTILLATION_PROMPT
from prompts.worker import SYSTEM_PROMPT

from agent.telemetry import ingest_tool_event, ToolEvent

# ------------------------------------------------------------------
# 0️⃣  Helpers
# ------------------------------------------------------------------
def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    

class Iteration(BaseModel):
    iteration: int
    model_response: Any = None
    model_response_compressed: Any = None
    tool_call_result: Any = None
    tool_call_result_compressed: Any = None
    tool_call_fingerprint: Optional[str] = None
    result_fingerprint: Optional[str] = None
    stagnant_count: int = 0

class Compaction(BaseModel):
    summary: List[dict] | None = []
    fallback: str = ""
    upto: int = 0          # history[:upto] is folded into summary


def merge_summaries(entries: List[dict]) -> dict:
    merged: Dict[str, list] = {}
    for entry in entries:
        for k, v in entry.items():
            bucket = merged.setdefault(k, [])
            bucket.extend(x for x in (v if isinstance(v, list) else [v]) if x not in bucket)
    return merged
    
def make_summary_message(compact: Compaction) -> List[HumanMessage]:
    if not compact.summary and not compact.fallback:
        return []
    body = json.dumps(merge_summaries(compact.summary), indent=2) if compact.summary else ""
    return [HumanMessage(content=f"Summary of earlier work (already done, do not repeat):\n{body}\n{compact.fallback}")]
    
def tool_call_fingerprint(tool_name: str, args: dict) -> str:
    payload = {
        "tool": tool_name,
        "args": args,
    }

    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
    
def result_fingerprint(result: Any) -> str:
    encoded = canonical_json(result).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def estimate_tokens(content: Any) -> int:
    return max(1, len(str(content)) // 4)

def fallback_mechanical_summary(msgs: List[BaseMessage]) -> str:
    lines = []
    for m in msgs:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                lines.append(f"call {tc['name']}({str(tc.get('args', ''))[:80]})")
        elif isinstance(m, ToolMessage):
            lines.append(f"result: {str(m.content)[:150]}")
     
    return "\n".join(lines)
        

def get_distillation(metrics: MetricsWrapper, 
                     distillation_llm: ChatOllama, 
                     compact: Compaction,
                     upto: int,
                     distill_these: List[Any]) -> List[HumanMessage]:
    print("Starting distill")
    conv_text = "\n".join(
        msg.content if isinstance(msg.content, str) else str(msg.content)
        for msg in distill_these
        if isinstance(msg, (HumanMessage, AIMessage, ToolMessage))
    )
    distillation_messages = [
        SystemMessage(content=DISTILLATION_PROMPT),
        HumanMessage(content=conv_text),
    ]
    distilled = False
    facts_json = None
    for _ in range(3):
        try:
            facts_json = distillation_llm.invoke(distillation_messages)
            raw = facts_json.content.strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw[raw.find("{"):raw.rfind("}") + 1]
            facts = json.loads(raw)
            if not isinstance(facts, dict): raise ValueError
            distilled = True

            metrics.emit(metrics.get_counter_message("distillation_success", "distillation agent worked"))
            break
        except Exception as exc:
            metrics.emit(metrics.get_counter_message("distillation_failure", "distillation agent crashes"))
            raw_content = facts_json.content if facts_json else "(no response)"
            print(f"Distillation JSON parse failed: {exc}")
            print(f"Raw model output (truncated): {raw_content[:300]}")

    print(f"Distilled: {distilled}")

    if distilled:
        compact.upto = upto
        compact.summary.append(facts)
        compact.fallback = ""
    else:
        compact.fallback = fallback_mechanical_summary(distill_these)
    
    print(compact.fallback)
    
    return compact 
        
HIGH, LOW = 15_000, 8_000

def iter_tokens(it: Iteration) -> int:
    r = it.tool_call_result_compressed or it.tool_call_result
    m = it.model_response_compressed or it.model_response
    return (estimate_tokens(r) + estimate_tokens(getattr(m, "content", ""))
            + estimate_tokens(getattr(m, "tool_calls", "")))

def derive_message_list(metrics: MetricsWrapper, 
                        distillation_llm: ChatOllama, 
                        compact: Compaction, 
                        permanent: List[BaseMessage],
                        history: List[Iteration]) -> List[Any]:
    """Build the message list to send to the LLM.

    The function walks the history in reverse (most recent first) and
    emits the latest non‑duplicate iteration.  Duplicates are detected
    via the ``step_fingerprint`` field.  For each iteration we emit
    the compressed version if present, otherwise the raw value.
    """
    seen_fingerprints = set()
    send_to_llm = []
    send_to_distill = []
        
    live_total = sum(iter_tokens(i) for i in history if i.iteration > compact.upto)
    token_quota = LOW if live_total > HIGH else float("inf")
    
    upto: int = 0
    list_to_add_to = send_to_llm
    last_upto = compact.upto
    for iteration in reversed(history):
    
        #only send to distill what has not yet been compacted
        if iteration.iteration <= last_upto:
            break
            
        fp = (iteration.tool_call_fingerprint, iteration.result_fingerprint)
        if fp in seen_fingerprints:
            # Skip earlier duplicate
            continue
            
        seen_fingerprints.add(fp)
        
        if token_quota < 0 and upto == 0:
            list_to_add_to = send_to_distill
            upto = iteration.iteration
        
        try:
            #we add these backwards because we are building from the end of the list
            token_quota -= iter_tokens(iteration) 
            if iteration.tool_call_result_compressed is not None:
                list_to_add_to.append(
                    ToolMessage(
                        content=str(iteration.tool_call_result_compressed),
                        tool_call_id=iteration.model_response.tool_calls[0]["id"],
                    )
                )
            else:
                list_to_add_to.append(
                    ToolMessage(
                        content=str(iteration.tool_call_result),
                        tool_call_id=iteration.model_response.tool_calls[0]["id"],
                    )
                )

            if iteration.model_response_compressed is not None:
                list_to_add_to.append(iteration.model_response_compressed)
            else:
                list_to_add_to.append(iteration.model_response)
        except Exception as e:
            print(e)
            print(iteration)
            raise
    
    if len(send_to_distill) > 0:
        send_to_distill.reverse()
        compact = get_distillation(metrics, distillation_llm, compact, upto, send_to_distill)
        
    send_to_llm.reverse()
    return compact, permanent + make_summary_message(compact) + send_to_llm
    
def run_agent(
    metrics: MetricsWrapper,
    config: dict,
    tools: dict,
    llm_with_tools: ChatOllama,
    distillation_llm: ChatOllama,
    user_request: str,
    max_iterations: int = 150,
    verbose: bool = False,
) -> Dict:
    operation_metric_labeler = metrics.get_counter_message_labeler(
        "operation", "agent general activity"
    )
    metrics.emit(operation_metric_labeler({"operation" : "begin loop"}))

    tool_call_metric_labeler = metrics.get_counter_message_labeler("tool_call", "the agent calls a tool")
    failure_metric_labeler = metrics.get_counter_message_labeler("tool_call_failure", "the agent tool fails")
    token_gauge = metrics.get_gauge_func("tokens_in_play", "tokens in current context")
    
    execution_id = str(uuid.uuid4())
    # expose execution id for tools that need it
    os.environ["CURRENT_EXECUTION_ID"] = execution_id
    permanent_messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]
    events: list[ToolEvent] = []
    iteration = 0
    event_counter = 0
    step_counts = {} #count of fingerprints to occurances
    
    full_thread_history: List[Iteration]  = []#model message list is derived from this
    
    current_compaction: Compaction = Compaction()
    
    # centralize tool event accumulation / ingest call details
    # using local state
    def add_tool_event(te: ToolEvent):
        nonlocal event_counter
        event_counter = event_counter + 1
        te.instance_number = event_counter
        events.append(te)
        #do not ingest nonsense events
        if not (te.event_type=="parse_error" or (te.event_type == "agent_response" and len(te.result) < 5)):
            ingest_tool_event(execution_id, te)
                
    while iteration < max_iterations:
        iteration = iteration + 1
        this_iteration = Iteration(
            iteration=iteration
        )
        if verbose:
            print(f"\n--- iteration {iteration} ---")
            
        metrics.emit(operation_metric_labeler({"operation" : "iterate"}))
        
        tool_calls = []
        response = {}
        current_compaction, send_to_llm = derive_message_list(metrics, distillation_llm, current_compaction, permanent_messages, full_thread_history)
        retry_notes: list[BaseMessage] = []
        for retry in range(10):
            
            try:
                response = llm_with_tools.invoke(send_to_llm + retry_notes)

                this_iteration.model_response = response
                
                tool_calls = response.tool_calls or []
                content = (response.content or "").strip()
                if len(tool_calls) == 1 or (not tool_calls and len(content) > 4):
                    break
                retry_notes += [response, HumanMessage("Your response was empty or invalid. Return exactly one tool call, or a final answer as content only.")]
            except ResponseError as e:
                retry_notes.append(HumanMessage(f"Last response failed tool-call parsing: {e}. Return exactly one valid tool call."))
        else:
            return {"condition": "model failed after 10 retries", 
                    "final_response": getattr(response, "content", "failure after retries"),
                    "iterations": iteration,
                    "events": events,
                    "execution_id" : execution_id}
                    
        if verbose:
            if response.content:
                print("Assistant:", response.content[:2000])

        # The model is finished when it returns content and no tool calls.
        if len(tool_calls) == 0:
        
            metrics.emit(operation_metric_labeler({"operation" : "completed"}))
            return {"condition" : "no tool calls",
                    "final_response": response.content,
                    "iterations": iteration,
                    "events": events,
                    "execution_id" : execution_id}
        
        add_tool_event(
            ToolEvent(
                iteration=iteration,
                event_type="agent_response",
                model_name=config['model'],
                args={},
                result=str(response.content)
            )
        )

        tool_call = tool_calls[0]
        #NOTE there will only be one tool call per the current rules
        tool_name = tool_call["name"]
        tool_args = tool_call.get("args", {})

        selected_tool = tools.get(tool_name)

        # an unknown tool is unknown regardless of args
        fp_args = tool_args if selected_tool is not None else {}
        call_fp = tool_call_fingerprint(tool_name, fp_args)

        if selected_tool is None:
            result = f"Unknown tool: {tool_name}. Available: {list(tools)}"
            metrics.emit(failure_metric_labeler({"failure": f"unknown tool {tool_name}"}))
        else:
            try:
                metrics.emit(tool_call_metric_labeler({"tool_call": tool_name}))
                result = selected_tool.invoke(tool_args)
            except Exception as exc:
                result = f"Tool error: {type(exc).__name__}: {exc}"
                metrics.emit(failure_metric_labeler({"failure": f"execution failure {tool_name}"}))

        this_iteration.tool_call_result=result
        this_iteration.result_fingerprint = result_fingerprint(this_iteration.tool_call_result)
        this_iteration.tool_call_fingerprint = call_fp
        step_fingerprint = (
            this_iteration.tool_call_fingerprint,
            this_iteration.result_fingerprint,
        )
        step_counts[step_fingerprint] = step_counts.get(step_fingerprint, -1) + 1
        this_iteration.stagnant_count=step_counts[step_fingerprint]
                
            
        add_tool_event(
            ToolEvent(
                iteration=iteration,
                event_type="tool_call_result",
                model_name=config['model'],
                tool=tool_name,
                args=tool_args,
                result=this_iteration.tool_call_result,
            )
        )
        
        print(f"Executing: {tool_name}({str(tool_args)[:50]})")

        full_thread_history.append(this_iteration)
            
        metrics.emit(token_gauge(getattr(response, "usage_metadata", {}).get("input_tokens", 0)))

    metrics.emit(operation_metric_labeler({"operation" : "ran out of turns"}))
    return {"condition" : f"Agent stopped after {max_iterations} iterations. The workspace may contain partial results.",
            "final_response": response.content,
            "iterations": iteration,
            "events": events,
            "execution_id" : execution_id}

