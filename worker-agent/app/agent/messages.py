from observability.metrics import MetricsWrapper
from langchain_ollama import ChatOllama
from langchain_core.messages import ToolMessage, BaseMessage
from typing import Any, List
from agent.models import Iteration, Compaction
from agent.compaction import make_summary_message, get_distillation
from agent.compression import compress_history

HIGH, LOW = 15_000, 8_000

def estimate_tokens(content: Any) -> int:
    return max(1, len(str(content)) // 4)
    
def iter_tokens(it: Iteration) -> int:
    """
        note that iter tokens defaults to the compressed values,
        this is only used for the count of tokens sent to the
        worker llm, when we switch to assembling distillation llm 
        message, we do not keep track of tokens
    """
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
    
    history = compress_history(metrics, history, compact.upto)
    
    upto: int = 0
    list_to_add_to = send_to_llm
    last_upto = compact.upto
    primary_result_attribute = "tool_call_result_compressed"
    primary_response_attribute = "model_response_compressed"
    for iteration in reversed(history):
    
        #only send to distill what has not yet been compacted
        if iteration.iteration < last_upto:
            break
            
        fp = (iteration.tool_call_fingerprint, iteration.result_fingerprint)
        if fp in seen_fingerprints:
            # Skip earlier duplicate
            continue
            
        seen_fingerprints.add(fp)
        
        if token_quota < 0 and upto == 0:
            list_to_add_to = send_to_distill
            upto = iteration.iteration
            #distillation LLM gets original uncompressed content
            primary_result_attribute = "tool_call_result"
            primary_response_attribute = "model_response"
        
        try:
            #we add these backwards because we are building from the end of the list
            token_quota -= iter_tokens(iteration)
            tool_content = f"{getattr(iteration, primary_result_attribute) or iteration.tool_call_result}"
            
            #only add stagnant nudge if this is sent to the llm, indicated by upto == 0
            if iteration.stagnant_count >= 2 and upto == 0:
                metrics.emit(metrics.get_counter_message("stagnation_warning_issued", "messages with high stagnation count"))
                tool_content = f"**NOTE**: this call has been used for the same result {iteration.stagnant_count + 1} times, \n **history is de-duplicated**\n do you need to continue calling this? tool result follows:\n{tool_content}"
                
            list_to_add_to.append(
                ToolMessage(
                    content=tool_content,
                    tool_call_id=iteration.model_response.tool_calls[0]["id"],
                )
            )

            list_to_add_to.append(getattr(iteration, primary_response_attribute) or iteration.model_response) 
        except Exception as e:
            print(e)
            print(iteration)
            raise
    
    if len(send_to_distill) > 0:
        send_to_distill.reverse()
        compact = get_distillation(metrics, distillation_llm, compact, upto, send_to_distill)
        
    send_to_llm.reverse()
        
    return compact, permanent + make_summary_message(compact) + send_to_llm
