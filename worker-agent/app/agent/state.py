"""
agent/state.py handles the progressive aggregation of existing agent state 
with incoming new state from summarizing the last truncation.

we will get the current compaction object containing the existing aggregation and the new state

the new state will be the last item in the summary list

we will prompt an llm with the structured output from 


"""
from prompts.distillation_delta import DELTA_ANALYSIS_PROMPT
from contracts.inference_contracts.agent_state_delta import DistillationDelta
from agent.models import Compaction
from contracts.inference_contracts.worker_agent_request import AgentRequest
from langchain_ollama import ChatOllama
from contracts.inference_contracts.info import InfoNode
from observability.metrics import MetricsWrapper
from agent.telemetry import ingest_agent_state_delta

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

def create_delta_llm(config: AgentRequest) -> ChatOllama:
    delta_llm = ChatOllama(
        model=config.distillation_delta_model,
        base_url=config.base_url,
        temperature=config.distillation_temp,
        num_ctx=config.distillation_num_ctx,
    ).with_structured_output(DistillationDelta)
    
    return delta_llm

def get_delta(config: AgentRequest, metrics: MetricsWrapper, info: InfoNode, compact: Compaction) -> DistillationDelta:

    delta_llm = create_delta_llm(config)
    
    conv_text = f"PRIOR_AGGREGATION:{json.dumps(compact.aggregation.model_dump(), indent=2)}\nLATEST_SUMMARY:{json.dumps(compact.states[-1].model_dump(), indent=2)}"
    #replace model dumps with projection calls
    
    delta_messages = [
        SystemMessage(content=DELTA_ANALYSIS_PROMPT),
        HumanMessage(content=conv_text),
    ]
    agent_state_delta = None
    
    retry_notes: list[BaseMessage] = []
    for _ in range(3):
        agent_state_delta = None
        try:
            agent_state_delta = delta_llm.invoke(delta_messages)
            if not isinstance(agent_state_delta, DistillationDelta):
                raise ValueError(f"expected a DistillationDelta object, got {type(agent_state_delta).__name__}")
                
            ingest_agent_state_delta(agent_state_delta, info)
            
            metrics.emit(metrics.get_counter_message("distillation_delta_success", "distillation delta agent worked"))
            break
        except Exception as exc:
            print(f"Distillation delta failed: {exc}")
            metrics.emit(metrics.get_counter_message("distillation_delta_failure", "distillation delta agent crashes"))
            raw_content = str(agent_state_delta) if agent_state_delta else "(no response)"
            print(f"Raw model output (truncated): {raw_content[:300]}")
            retry_notes.append(HumanMessage(f"Last response failed validation: {exc}. Please try again."))

    if agent_state_delta is None:
        raise ValueError("delta extraction failed")
        
    return agent_state_delta

