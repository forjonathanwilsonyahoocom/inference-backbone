import os
from observability.metrics import MetricsWrapper
from typing import Any, List, Optional, Dict
from pydantic import BaseModel
from ollama import ResponseError 
from agent.messages import derive_message_list
from agent.models import Iteration, Compaction
from agent.fingerprint import tool_call_fingerprint, result_fingerprint

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)

from langchain_ollama import ChatOllama
from langchain_core.tools import tool

from prompts.worker import SYSTEM_PROMPT

from agent.telemetry import ingest_tool_event, ToolEvent


    
def run_agent(
    metrics: MetricsWrapper,
    config: dict,
    tools: dict,
    llm_with_tools: ChatOllama,
    distillation_llm: ChatOllama,
    user_request: str,
    execution_id: str,
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
            this_iteration.tool_name = tool_name
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
        
        print(f"Executing: {tool_name}({str(tool_args)[:150]})")

        full_thread_history.append(this_iteration)
            
        metrics.emit(token_gauge(getattr(response, "usage_metadata", {}).get("input_tokens", 0)))

    metrics.emit(operation_metric_labeler({"operation" : "ran out of turns"}))
    return {"condition" : f"Agent stopped after {max_iterations} iterations. The workspace may contain partial results.",
            "final_response": response.content,
            "iterations": iteration,
            "events": events,
            "execution_id" : execution_id}

