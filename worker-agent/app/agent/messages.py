#messages.py
from observability.metrics import MetricsWrapper
from langchain_ollama import ChatOllama
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage
from typing import Any, List
from agent.models import Iteration, Compaction, ToolCallResultWrapper
from contracts.inference_contracts.worker_agent_request import AgentRequest
from agent.compaction import make_summary_message, get_distillation
from agent.compression import compress_history


def estimate_tokens(content: Any) -> int:
    return max(1, len(str(content)) // 4)
    
def iter_tokens(it: Iteration,
                primary_response_attribute: str  = "model_response_compressed") -> int:
    """
        note that iter tokens defaults to the compressed values,
        this is only used for the count of tokens in the active window for hysteresis
    """
    m = getattr(it, primary_response_attribute) or it.model_response
    return (estimate_tokens(getattr(m, "content", ""))
            + estimate_tokens(getattr(m, "tool_calls", "")))

def tool_tokens(wrapper: ToolCallResultWrapper,
                primary_result_attribute: str = "tool_call_result_compressed") -> int:
    """
        note that tool_tokens defaults to the compressed values,
        this is only used for the count of tokens in the active window for hysteresis
    """
    r = getattr(wrapper, primary_result_attribute) or wrapper.tool_call_result
    return estimate_tokens(r) 

def deduped_distillation(config: AgentRequest,
                       metrics: MetricsWrapper, 
                       distillation_llm: ChatOllama, 
                       compact: Compaction, 
                       history: List[Iteration],
                       all_the_way_to_end: bool = True) -> (Compaction, str):
    """distill all new messages at the end of the thread.
    to create the ingested AgentState records and the distillation summary

    The function walks the history in reverse (most recent first) and
    holds the latest non‑duplicate iteration.  Duplicates are detected
    via the ``step_fingerprint`` field. 
    
    we stop when we reach the beginning or the upto on the compaction
    
    then we walk forwards over the de-duplicated content For each iteration we emit
    the raw value and only send to the distillation agent, we continue 
    until we reach the end.
    
    optionally we distill the final remaining messages in the buffer
    """
    print(f"deduped_distillation, all_the_way_to_end = {all_the_way_to_end} ")
    seen_fingerprints = set()
    send_to_distill = []
        
    token_quota = config.distill_at
        
    deduplicated: List[Iteration] = []
    skip_duplicated_result = set()
    last_upto = compact.upto
    for iteration in reversed(history):
        #only send to distill what has not yet been compacted
        if iteration.iteration < last_upto:
            break
        iteration_has_unique = False
        for wrapper in reversed(iteration.tool_call_results):
            fp = (wrapper.tool_call_fingerprint, wrapper.result_fingerprint)
            if fp in seen_fingerprints:
                # Skip earlier duplicate
                skip_duplicated_result.add(wrapper.tool_call_id)
                continue
            iteration_has_unique = True
            seen_fingerprints.add(fp)
        
        if iteration_has_unique:
            deduplicated.append(iteration)
        
    for iteration in reversed(deduplicated):
        if token_quota < 0:
            compact = get_distillation(config, metrics, distillation_llm, compact, iteration.iteration, send_to_distill)
            send_to_distill = []
            token_quota = config.distill_at
        
        token_quota -= iter_tokens(iteration, "model_response")
                    
        send_to_distill.append(iteration.model_response) 
    
        for wrapper in iteration.tool_call_results:
            if not wrapper.tool_call_id in skip_duplicated_result:
                tool_content = f"{wrapper.tool_call_result}"
                if wrapper.tool_call_result_utility is not None or wrapper.tool_call_result_chunk_query is not None:
                    tool_content = f"result_assessed: utility={getattr(wrapper, 'tool_call_result_utility', 'not assessed')}, better_focus={wrapper.tool_call_result_chunk_query}\n{tool_content}"
                token_quota -= tool_tokens(wrapper, "tool_call_result")
                send_to_distill.append(
                    ToolMessage(
                        content=tool_content,
                        tool_call_id=wrapper.tool_call_id,
                    )
                )

    
    if all_the_way_to_end and len(send_to_distill) > 0:
        compact = get_distillation(config, metrics, distillation_llm, compact, history[-1].iteration, send_to_distill)
        
    summary =  make_summary_message(compact, not all_the_way_to_end)
        
    return compact, summary

def derive_message_list(config: AgentRequest,
                        metrics: MetricsWrapper, 
                        distillation_llm: ChatOllama, 
                        compact: Compaction, 
                        history: List[Iteration]) -> (Compaction, List[Any]):
    """Build the message list to send to the LLM.

    The function walks the history in reverse (most recent first) and
    emits the latest non‑duplicate iteration.  Duplicates are detected
    via the ``step_fingerprint`` field.  For each iteration we emit
    the compressed version if present, otherwise the raw value.
    """
    
    stagnation_metric_labeler = metrics.get_counter_message_labeler("stagnation_warning", "the agent calls a tool on repeat")
    layer_metric_labeler = metrics.get_gauge_labeler_func("estimated_tokens_by_layer", "compressed message layers")
    seen_fingerprints = set()
    send_to_llm = []
    
    history = compress_history(config, metrics, history, compact.upto)
    
    compact, summary = deduped_distillation(config, metrics, distillation_llm, compact, history, False)
    
    live_total = 0
    layer = 0
    for iteration in reversed(history):
        
        if live_total < config.truncate_at:
            live_total += iter_tokens(iteration)
            layer += 1
            metrics.emit(layer_metric_labeler({"layer" : str(layer)}, live_total))
            for result_wrapper in iteration.tool_call_results:
                live_total += tool_tokens(result_wrapper)
                layer += 1
                metrics.emit(layer_metric_labeler({"layer" : str(layer)}, live_total))
        else:
            #stop counting
            break

    token_quota = config.truncate_at

    is_first_message = True
        
    for iteration in reversed(history):
            
        if token_quota < 0:
            #we are at the truncate boundary
            break

        token_quota -= iter_tokens(iteration)
        
        try:
            for wrapper in reversed(iteration.tool_call_results):
                
                fp = (wrapper.tool_call_fingerprint, wrapper.result_fingerprint)
                if fp in seen_fingerprints:
                    # Skip earlier duplicate
                    continue
                    
                seen_fingerprints.add(fp)
                               
                if wrapper.is_silenced:
                    continue
            
                #we add these backwards because we are building from the end of the list
                tool_content = f"{getattr(wrapper, 'tool_call_result_compressed') or wrapper.tool_call_result}"

                token_quota -= tool_tokens(wrapper)
    
                preface = f"instance_number={wrapper.tool_call_result_instance_number}\n"
                if is_first_message:
                    preface += f"turn {iteration.iteration} of max {config.max_iterations}, {config.max_iterations - iteration.iteration} turns remaining\n"
                    if config.max_iterations - iteration.iteration <=2:
                        preface += "# use remaining turns to wrap up this execution sequence and respond\n"
                    is_first_message = False

                if wrapper.stagnant_count >= 2:
                    metrics.emit(stagnation_metric_labeler({"tool_call" : wrapper.tool_name}))
                    preface += f"""**NOTE**
this call has been used for the same result {wrapper.stagnant_count + 1} times,
*history is de-duplicated**
do you need to continue calling this?
tool result follows:\n"""
               
                tool_content = f"{preface}{tool_content}"
                    
                if wrapper.tool_call_result_utility is not None :
                     preface += f"result_assessed: utility={wrapper.tool_call_result_utility} \n"
                if wrapper.tool_call_result_chunk_query is not None:
                     preface += f"result_assessed: better_focus={wrapper.tool_call_result_chunk_query}\n"
                    
                send_to_llm.append(
                    ToolMessage(
                        content=tool_content,
                        tool_call_id=wrapper.tool_call_id,
                    )
                )

            send_to_llm.append(getattr(iteration, 'model_response_compressed') or iteration.model_response) 
        except Exception as e:
            print(e)
            print(iteration)
            raise
            
    send_to_llm.reverse()
    
    permanent = [
        SystemMessage(content=config.system_message),
        HumanMessage(content=f"{config.request}\n{summary}"),
    ]
        
    return compact, permanent + send_to_llm
    
