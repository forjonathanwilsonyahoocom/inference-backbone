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
    seen_fingerprints = set()
    send_to_llm = []
    send_to_distill = []
        
    
    live_total = 0
    for i in history:
        if i.iteration > compact.upto:
            live_total += iter_tokens(i)
            for w in i.tool_call_results:
                live_total += tool_tokens(w)

    token_quota = config.distill_to if live_total > config.distill_at else float("inf")
    
    history = compress_history(config, metrics, history, compact.upto)
    
    upto: int = 0
    list_to_add_to = send_to_llm
    last_upto = compact.upto
    primary_result_attribute = "tool_call_result_compressed"
    primary_response_attribute = "model_response_compressed"
    is_first_message = True
    for iteration in reversed(history):
    
        #only send to distill what has not yet been compacted
        if iteration.iteration < last_upto:
            break

        
        if token_quota < 0 and upto == 0:
            list_to_add_to = send_to_distill
            token_quota = config.distill_to
            upto = iteration.iteration
            #distillation LLM gets original uncompressed content
            primary_result_attribute = "tool_call_result"
            primary_response_attribute = "model_response"
        
        if token_quota < 0 and len(send_to_distill) > 0:
            send_to_distill.reverse()
            compact = get_distillation(config, metrics, distillation_llm, compact, iteration.iteration, send_to_distill)
            send_to_distill = []
            token_quota = config.distill_to

        token_quota -= iter_tokens(iteration, primary_response_attribute)
        
        try:
            for wrapper in reversed(iteration.tool_call_results):
                
                fp = (wrapper.tool_call_fingerprint, wrapper.result_fingerprint)
                if fp in seen_fingerprints:
                    # Skip earlier duplicate
                    continue
                    
                seen_fingerprints.add(fp)
                               
                if upto == 0 and wrapper.is_silenced: #we will only send silenced tools to the distillation context
                    continue
            
                #we add these backwards because we are building from the end of the list
                tool_content = f"{getattr(wrapper, primary_result_attribute) or wrapper.tool_call_result}"

                token_quota -= tool_tokens(wrapper, primary_result_attribute)
        
                if upto == 0:
                    preface = f"instance_number={wrapper.tool_call_result_instance_number}\n"
                    if is_first_message:
                        preface += f"turn {iteration.iteration} of max {config.max_iterations}, {config.max_iterations - iteration.iteration} turns remaining\n"
                        if config.max_iterations - iteration.iteration <=2:
                            preface += "# use remaining turns for wrapping up this execution sequence\n"
                        is_first_message = False
                    #only add stagnant nudge if this is sent to the llm, indicated by upto == 0
                    if wrapper.stagnant_count >= 2:
                        metrics.emit(stagnation_metric_labeler({"tool_call" : wrapper.tool_name}))
                        preface += f"**NOTE**: this call has been used for the same result {wrapper.stagnant_count + 1} times, \n **history is de-duplicated**\n do you need to continue calling this? tool result follows:\n{tool_content}"
                   
                    tool_content = f"{preface}{tool_content}"
                    
                if wrapper.tool_call_result_utility is not None or wrapper.tool_call_result_chunk_query is not None:
                    tool_content = f"result_assessed: utility={wrapper.tool_call_result_utility}, better_focus={wrapper.tool_call_result_chunk_query}\n{tool_content}"
                list_to_add_to.append(
                    ToolMessage(
                        content=tool_content,
                        tool_call_id=wrapper.tool_call_id,
                    )
                )

            list_to_add_to.append(getattr(iteration, primary_response_attribute) or iteration.model_response) 
        except Exception as e:
            print(e)
            print(iteration)
            raise
    
    if len(send_to_distill) > 0:
        send_to_distill.reverse()
        compact = get_distillation(config, metrics, distillation_llm, compact, upto, send_to_distill)
        
    send_to_llm.reverse()
    
    permanent = [
        SystemMessage(content=config.system_message),
        HumanMessage(content=f"{config.request}\n{make_summary_message(compact, True)}"),
    ]
        
    return compact, permanent + send_to_llm
    

def final_distillation(config: AgentRequest,
                       metrics: MetricsWrapper, 
                       distillation_llm: ChatOllama, 
                       compact: Compaction, 
                       history: List[Iteration]) -> (Compaction, str):
    """distill all remaining messages at the end of the thread.
    this is primarily to create the ingested AgentState records

    The function walks the history in reverse (most recent first) and
    holds the latest non‑duplicate iteration.  Duplicates are detected
    via the ``step_fingerprint`` field. 
    
    we stop when we reach the beginning or the upto on the compaction
    
    then we walk forwards over the de-duplicated content For each iteration we emit
    the raw value and only send to the distillation agent, we continue 
    until we reach the end.
    """
    print("final_distillation")
    seen_fingerprints = set()
    send_to_distill = []
        
    token_quota = config.distill_to
        
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
            token_quota = config.distill_to
        
        token_quota -= iter_tokens(iteration, "model_response")
                    
        send_to_distill.append(iteration.model_response) 
    
        for wrapper in iteration.tool_call_results:
            if not wrapper.tool_call_id in skip_duplicated_result:
                tool_content = f"{wrapper.tool_call_result}"
                token_quota -= tool_tokens(wrapper, "tool_call_result")
                send_to_distill.append(
                    ToolMessage(
                        content=tool_content,
                        tool_call_id=wrapper.tool_call_id,
                    )
                )

    
    if len(send_to_distill) > 0:
        compact = get_distillation(config, metrics, distillation_llm, compact, history[-1].iteration, send_to_distill)
    summary =  make_summary_message(compact)
        
    return compact, summary

