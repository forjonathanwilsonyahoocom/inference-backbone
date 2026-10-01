import json
import os
import uuid
from observability.metrics import MetricsWrapper
import hashlib
from typing import Any, Tuple, List
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
SUMMARY_TAG = "__DISTILLED_SUMMARY__"  # sentinel prefix, not inferred from position/type

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
    tool_call_fingerprint: str = None
    result_fingerprint: str = None
    stagnant_count: int = 0
    
def make_summary_message(facts: dict) -> HumanMessage:
    return HumanMessage(content=SUMMARY_TAG + json.dumps(facts, indent=2))

def is_summary_message(msg: BaseMessage) -> bool:
    return isinstance(msg, HumanMessage) and msg.content.startswith(SUMMARY_TAG)

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
    
def get_distillation(distillation_llm: ChatOllama, distill_these: List[Any]) -> List[HumanMessage]:
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
            distilled = True

            metrics.emit(metrics.get_counter_message("distillation_success", "distillation agent worked"))
            break
        except Exception as exc:
            metrics.emit(metrics.get_counter_message("distillation_failure", "distillation agent crashes"))
            raw_content = facts_json.content if facts_json else "(no response)"
            print(f"Distillation JSON parse failed: {exc}")
            print(f"Raw model output (truncated): {raw_content[:300]}")


    print("Distilled")
    print(facts_json)

    if distilled:
        return [make_summary_message(facts)]
    else:
        return [make_summary_message({"message_summary_failed" : "oldest messages have been truncated"})]

def derive_message_list(distillation_llm: ChatOllama, permanent: List[BaseMessage], history: List[Iteration]) -> List[Any]:
    """Build the message list to send to the LLM.

    * ``permanent`` – system + user + any permanent messages.
    * ``history`` – list of ``Iteration`` objects.

    The function walks the history in reverse (most recent first) and
    emits the latest non‑duplicate iteration.  Duplicates are detected
    via the ``step_fingerprint`` field.  For each iteration we emit
    the compressed version if present, otherwise the raw value.
    """
    seen_fingerprints = set()
    send_to_llm = []
    send_to_distill = []
    
    token_quota = 15000
    
    list_to_add_to = send_to_llm
    for iteration in reversed(history):
        fp = (iteration.tool_call_fingerprint, result_fingerprint)
        if fp in seen_fingerprints:
            # Skip earlier duplicate
            continue
        seen_fingerprints.add(fp)
        
        if token_quota < 0:
            list_to_add_to = send_to_distill
        
        try:
            #we add these backwards because we are building from the end of the list
            if iteration.tool_call_result_compressed is not None:
                token_quota = token_quota - estimate_tokens(iteration.tool_call_result_compressed)
                list_to_add_to.append(
                    ToolMessage(
                        content=str(iteration.tool_call_result_compressed),
                        tool_call_id=iteration.model_response.tool_calls[0]["id"],
                    )
                )
            else:
                token_quota = token_quota - estimate_tokens(iteration.tool_call_result)
                list_to_add_to.append(
                    ToolMessage(
                        content=str(iteration.tool_call_result),
                        tool_call_id=iteration.model_response.tool_calls[0]["id"],
                    )
                )

            if iteration.model_response_compressed is not None:
                token_quota = token_quota - estimate_tokens(iteration.model_response_compressed)
                list_to_add_to.append(iteration.model_response_compressed)
            else:
                token_quota = token_quota - estimate_tokens(iteration.model_response)
                list_to_add_to.append(iteration.model_response)
        except Exception as e:
            print(e)
            print(iteration)
            raise
    distilled = []
    
    if len(send_to_distill) > 0:
        send_to_distill.reverse()
        distilled = get_distillation(send_to_distill)
        

    send_to_llm.reverse()
    return permanent + distilled + send_to_llm
    
def run_agent(
    metrics: MetricsWrapper,
    config: dict,
    tools: dict,
    llm_with_tools: ChatOllama,
    distillation_llm: ChatOllama,
    user_request: str,
    max_iterations: int = 150,
    verbose: bool = False,
) -> str:
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
            iteration=iteration,
            compressed=False,
        )
        if verbose:
            print(f"\n--- iteration {iteration + 1} ---")
            
        metrics.emit(operation_metric_labeler({"operation" : "iterate"}))
        
        tool_calls = []
        response = {}
        for retry in range(10):
            
            send_to_llm = derive_message_list(distillation_llm, permanent_messages, full_thread_history)
            try:
                response = llm_with_tools.invoke(send_to_llm)

                this_iteration.model_response = response
                
                tool_calls = response.tool_calls or []
                content = response.content or ""
                
                if len(tool_calls) == 1 or len(content.strip()) > 4:
                    break #continue 
                else:
                    #this fake tool call insertion is just to keep the derivation consistant
                    this_iteration.model_response.tool_calls = [{"id" : str(uuid.uuid4()), "name" : "no_valid_call_was_made"}]
                    this_iteration.tool_call_result = "Your response was empty or unusable.  Return one valid tool call or content only."
                    
                    #NOTE this may result in multiple iteration objects with no fingerprints for the same iteration
                    #that is ok since the derived list will only keep the most recent of those 
                    full_thread_history.append(this_iteration)

            except ResponseError as e:
                raw_content = str(e)

                print("ResponseError ", raw_content)
                add_tool_event(
                    ToolEvent(
                        iteration=iteration,
                        event_type="parse_error",
                        model_name=config['model'],
                        args={},
                        result={"error": str(e), "raw_output": raw_content},
                    )
                )
                
                metrics.emit(failure_metric_labeler({"failure" : "parsing error"}))

                this_iteration.tool_call_result = HumanMessage(
                        content=(
                            "Last response failed tool-call parsing.\n"
                            f"Error: {e}\n"
                            "Return exactly one valid tool call."
                        )
                    )
                #NOTE this may result in multiple iteration objects with no fingerprints for the same iteration
                #that is ok since the derived list will only keep the most recent of those 
                full_thread_history.append(this_iteration)
        else:
            # Ten retries failed.
            print("Model failed to produce a valid response after 10 retries")
            
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

        for tool_call in tool_calls:
            #NOTE there will only be one tool call per the current rules
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})

            selected_tool = tools.get(tool_name)

            if selected_tool is None:
                this_iteration.tool_call_result= f"Unknown tool: {tool_name}"
                metrics.emit(failure_metric_labeler({"failure" : f"unknown tool {tool_name}"}))
            else:
                try:
                    metrics.emit(tool_call_metric_labeler({"tool_call" : tool_name}))
                    tool_result = selected_tool.invoke(tool_args)
                    this_iteration.tool_call_result = tool_result
                    this_iteration.tool_call_fingerprint= tool_call_fingerprint(tool_name, tool_args)
                    this_iteration.result_fingerprint=result_fingerprint(tool_result)
                    step_fingerprint = (
                        this_iteration.tool_call_fingerprint,
                        this_iteration.result_fingerprint,
                    )

                    step_counts[step_fingerprint] = step_counts.get(step_fingerprint, 0) + 1
                    this_iteration.stagnant_count=step_counts[step_fingerprint]
                    
                except Exception as exc:
                    this_iteration.tool_call_result = f"Tool error: {type(exc).__name__}: {exc}"

            
            add_tool_event(
                ToolEvent(
                    iteration=iteration,
                    event_type="tool_call_result",
                    model_name=config['model'],
                    tool=tool_name,
                    args=tool_args,
                    result=tool_result,
                )
            )
            
            print(f"Executing: {tool_name}({str(tool_args)[:50]})")


        full_thread_history.append(this_iteration)
            
        metrics.emit(token_gauge(response.usage_metadata.get("input_tokens", 0) ))

    metrics.emit(operation_metric_labeler({"operation" : "ran out of turns"}))
    return {"condition" : f"Agent stopped after {max_iterations} iterations. The workspace may contain partial results.",
            "final_response": response.content,
            "iterations": iteration,
            "events": events,
            "execution_id" : execution_id}

