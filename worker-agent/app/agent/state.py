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
from agent.models import AgentRequest
from langchain_ollama import ChatOllama
from agent.telemetry import ingest_agent_state_delta

def create_delta_llm(config: AgentRequest) -> ChatOllama:
    delta_llm = ChatOllama(
        model=config.distillation_delta_model,
        base_url=config.base_url,
        temperature=config.distillation_temp,
        num_ctx=config.distillation_num_ctx,
    ).with_structured_output(DistillationDelta)
    
    return delta_llm

def get_delta(config: AgentRequest,  compaction: Compaction) -> Compaction:

    delta_llm = create_delta_llm(config)
    
    if len(compaction.summary) > 1:
        prior = getattr(compaction, "summary_aggregate", compaction.summary[-2])
        conv_text = f"PRIOR_AGGREGATION:{prior}\nLATEST_SUMMARY:{compaction.summary[-1]}"
        delta_messages = [
            SystemMessage(content=DELTA_ANALYSIS_PROMPT),
            HumanMessage(content=conv_text),
        ]
        facts_delta = None
        for _ in range(3):
            agent_state_delta = None
            try:
                agent_state_delta = delta_llm.invoke(delta_messages)
                if not isinstance(agent_state_delta, DistillationDelta):
                    raise ValueError(f"expected a DistillationDelta object, got {type(agent_state_delta).__name__}")
                    
                info = InfoNode(id = f"{config.execution_id}-{compaction.upto}",
                                execution_id=config.execution_id,
                                instance_number_start=compaction.upto,
                                )
                ingest_agent_state_delta(agent_state_delta, info)

                facts_delta = agent_state_delta.model_dump()
                if not isinstance(facts_delta, dict):
                    raise ValueError(f"expected a dict from DistillationDelta.model_dump(), got {type(facts_delta).__name__}")
                
                metrics.emit(metrics.get_counter_message("distillation_delta_success", "distillation delta agent worked"))
                compaction.summary_deltas.append(facts_delta)
                break
            except Exception as exc:
                print(f"Distillation delta failed: {exc}")
                metrics.emit(metrics.get_counter_message("distillation_delta_failure", "distillation delta agent crashes"))
                raw_content = str(agent_state_delta) if agent_state_delta else "(no response)"
                print(f"Raw model output (truncated): {raw_content[:300]}")

    return compaction

