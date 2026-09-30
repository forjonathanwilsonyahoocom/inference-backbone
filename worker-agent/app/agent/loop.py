import json
import os
import uuid
from observability.metrics import MetricsWrapper
import hashlib
from typing import Any, Tuple, List
from pydantic import BaseModel
from ollama import ResponseError 
from collections import deque
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
from agent.truncation import truncate_history

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
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ]
    events: list[ToolEvent] = []
    iteration = 0
    event_counter = 0
    recent_steps = deque(maxlen=12)
    step_counts = {}

    # centralize tool event accumulation details
    # using local state
    def add_tool_event(te: ToolEvent):
        nonlocal event_counter
        event_counter = event_counter + 1
        te.instance_number = event_counter
        events.append(te)
        if te.event_type!="parse_error":
            ingest_tool_event(execution_id, te)

        
    while iteration < max_iterations:
        iteration = iteration + 1
        if verbose:
            print(f"\n--- iteration {iteration + 1} ---")
            
        metrics.emit(operation_metric_labeler({"operation" : "iterate"}))
        
        tool_calls = []
        response = {}
        for retry in range(10):
            try:
                response = llm_with_tools.invoke(messages)

                tool_calls = response.tool_calls or []
                content = response.content or ""

                if tool_calls or len(content.strip()) > 4:
                    break

                messages.append(
                    AIMessage(content=content)
                )
                messages.append(
                    HumanMessage(
                        content=(
                            "Your response was empty or unusable. "
                            "Return one valid tool call or content only."
                        )
                    )
                )

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
                messages.append(AIMessage(content=raw_content[:2000]))
                messages.append(
                    HumanMessage(
                        content=(
                            "The output above failed tool-call parsing.\n"
                            f"Error: {e}\n"
                            "Return exactly one valid tool call. "
                            "Do not explain your reasoning."
                        )
                    )
                )
                print("trying again")

        else:
            # Ten retries failed.
            print("Model failed to produce a valid response after 10 retries")
            

        messages.append(response)

        print("there are currently ",len(messages), " messages in the context")
        
        if verbose:
            if response.content:
                print("Assistant:", response.content[:2000])

        # The model is finished when it returns content and no tool calls.
        if len(tool_calls) == 0:
            if verbose:
                if response.content:
                    print("Assistant:", response.content)
            
            metrics.emit(operation_metric_labeler({"operation" : "completed"}))
            return {"condition" : "no tool calls",
                    "final_response": response.content,
                    "iterations": iteration,
                    "events": events,
                    "execution_id" : execution_id}
                    
        
        if response.content:
            add_tool_event(
                ToolEvent(
                    iteration=iteration,
                    event_type="agent_response",
                    model_name=config['model'],
                    args={},
                    result=str(response)
                )
            )


        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call["id"]

            selected_tool = tools.get(tool_name)

            if selected_tool is None:
                tool_result = f"Unknown tool: {tool_name}"

                metrics.emit(failure_metric_labeler({"failure" : f"unknown tool {tool_name}"}))
                # 2. Don't count this as a real iteration
                iteration = iteration - 1
            else:
                try:
                    metrics.emit(tool_call_metric_labeler({"tool_call" : tool_name}))
                    tool_result = selected_tool.invoke(tool_args)
                    # Ingest the tool result into evidence
                    
                    step_fingerprint = (
                        tool_call_fingerprint(tool_name, tool_args),
                        result_fingerprint(tool_result),
                    )

                    recent_steps.append(step_fingerprint)

                    step_counts[step_fingerprint] = step_counts.get(step_fingerprint, 0) + 1
                    
                    if step_counts[step_fingerprint] > 2:

                        metrics.emit(failure_metric_labeler({"failure" : "stagnation detected"}))
                        tool_result = ({
                            "status": "stagnation_detected",
                            "message": (
                                "This tool call has been repeated and produced the same result. "
                                "Do not repeat it with the same arguments."
                            ),
                            "tool": tool_name,
                            "arguments": tool_args,
                            "repeated_count": step_counts[step_fingerprint],
                            "result" : tool_result,
                            "suggested_actions": [
                                "Use a different query or arguments",
                                "Use another tool",
                                "Apply the information already returned",
                                "Finish if the task is complete",
                            ],
                        })
                        print(tool_result)

                    
                except Exception as exc:
                    tool_result = (
                        f"Tool error: {type(exc).__name__}: {exc}"
                    )

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
            
            if verbose:
                print(f"Executing: {tool_name}({str(tool_args)[:200]})")
                print(str(tool_result)[:200])
            else:
                print(f"Executing: {tool_name}()")

            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call_id,
                )
            )
        
        metrics.emit(token_gauge(response.usage_metadata.get("input_tokens", 0) ))

        # Distillation now runs AFTER all tool results for this turn are in. Thanks Claude
        if response.usage_metadata.get("input_tokens", 0) > 20_000:
            print("Starting distill")
            conv_text = "\n".join(
                msg.content if isinstance(msg.content, str) else str(msg.content)
                for msg in messages
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

            if verbose:
                print("Distilled")
                print(facts_json)
            else:
                print("Distilled")


            if distilled:
                summary_msg = make_summary_message(facts)
                if len(messages) > 2 and is_summary_message(messages[2]):
                    messages = messages[:2] + [summary_msg] + messages[3:]
                else:
                    messages = messages[:2] + [summary_msg] + messages[2:]

                messages = truncate_history(messages, max_tokens=15_000, preserve=3)
    
    metrics.emit(operation_metric_labeler({"operation" : "ran out of turns"}))
    return {"condition" : f"Agent stopped after {max_iterations} iterations. The workspace may contain partial results.",
            "final_response": response.content,
            "iterations": iteration,
            "events": events,
            "execution_id" : execution_id}

