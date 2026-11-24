from typing import Dict, Any, List
from observability.metrics import MetricsWrapper
from agent.models import Compaction
from contracts.inference_contracts.worker_agent_request import AgentRequest
from agent.state import get_delta
from prompts.distillation import DISTILLATION_PROMPT
from contracts.inference_contracts.agent_state import AgentState
from contracts.inference_contracts.info import InfoNode
from agent.telemetry import ingest_agent_state, ingest_agent_state_aggregate
from agent.apply_delta import apply_delta_to_aggregate
from agent.extend_agent_state import extend_state
from agent.state_projection.projection_dispatcher import project_for_worker
from langchain_ollama import ChatOllama
import json

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)

#clean this up after we switch to ExtendedAgentState projections
def make_summary_message(compact: Compaction, is_going_back_to_llm: bool = False) -> str:
    if not compact.aggregation_worker_projection and not compact.fallback:
        return ""
    body = ""
    if compact.aggregation_worker_projection:
    
        # Use the worker projection to generate the squished view for the LLM
        body = compact.aggregation_worker_projection
        
    if is_going_back_to_llm:
        return f"the initial {compact.upto} iterations have been compacted into this report:\n{body}\n{compact.fallback}"
    else:
        return  f"{body}\n{compact.fallback}"


#maybe clean this up after we switch to ExtendedAgentState projections
def fallback_mechanical_summary(msgs: List[BaseMessage]) -> str:
    lines = []
    for m in msgs:
        if isinstance(m, AIMessage):
            for tc in m.tool_calls or []:
                lines.append(f"call {tc['name']}({str(tc.get('args', ''))[:80]})")
        elif isinstance(m, ToolMessage):
            lines.append(f"result: {str(m.content)[:150]}")
     
    return "\n".join(lines)
        
def clip(value: Any, limit: int = 2000) -> str:
    s = str(value)
    return s if len(s) <= limit else s[:limit] + f"...[truncated {len(s) - limit} chars]"

def distillation_assembly(msgs: List[BaseMessage]) -> str:
    lines = []
    for m in msgs:
        if isinstance(m, AIMessage):
            if m.content:
                lines.append(f"LLM States: {clip(m.content)}")
            for tc in m.tool_calls or []:
                lines.append(f"call {tc['name']}({clip(tc.get('args', ''))})")
        elif isinstance(m, ToolMessage):
            lines.append(f"result: {clip(m.content)}")
    return "\n".join(lines)

def get_distillation(config: AgentRequest,
                     metrics: MetricsWrapper, 
                     distillation_llm: ChatOllama, 
                     compact: Compaction,
                     upto: int,
                     distill_these: List[Any]) -> Compaction:
    print(f"Starting distill from {compact.upto} to {upto}")
    
    conv_text = distillation_assembly(distill_these)
    
    input_len = len(conv_text)
    
    distillation_messages = [
        SystemMessage(content=DISTILLATION_PROMPT),
        HumanMessage(content=conv_text),
    ]

    retry_notes: list[BaseMessage] = []
    
    agent_state_facts = None
    for _ in range(3):
        agent_state_facts = None
        try:
            agent_state_facts = distillation_llm.invoke(distillation_messages + retry_notes)
            if not isinstance(agent_state_facts, AgentState):
                raise ValueError(f"expected a AgentState object, got {type(agent_state_facts).__name__}")
            
            output_len = len(json.dumps(agent_state_facts.model_dump()))
            if output_len > input_len * 1.2:
                raise ValueError(f"size of resulting distillation too large {output_len} compared to input {input_len}, it should be the same size or smaller")
                
            metrics.emit(metrics.get_counter_message("distillation_success", "distillation agent worked"))
            break
        except Exception as exc:
            print(f"Distillation failed: {exc}")
            metrics.emit(metrics.get_counter_message("distillation_failure", "distillation agent crashes"))
            raw_content = str(agent_state_facts) if agent_state_facts else "(no response)"
            print(f"Raw model output (truncated): {raw_content[:300]}")
            retry_notes.append(HumanMessage(f"Last response failed validation: {exc}. Please try again."))


    if agent_state_facts is not None:
        info = InfoNode(id = f"{config.execution_id}-{upto}",
                    execution_id=config.execution_id,
                    instance_number_start=compact.upto,
                    instance_number_end=upto,
                    )
        ingest_agent_state(agent_state_facts, info)
            
        extended = extend_state(upto, agent_state_facts)
        
        compact.upto = upto
        compact.fallback = ""
        compact.states.append(extended)
        if compact.aggregation is None:
            compact.aggregation = extended
        else:
            new_delta = get_delta(config, metrics, info, compact)
            compact.summary_deltas.append(new_delta)
            compact.aggregation = apply_delta_to_aggregate(metrics, compact.aggregation, extended, new_delta)
            ingest_agent_state_aggregate(compact.aggregation, info)

        compact.aggregation_worker_projection = project_for_worker(compact.aggregation)
        
        if config.verbose:
            print(compact.aggregation_worker_projection)

    else:
        metrics.emit(metrics.get_counter_message("distillation_fallback", "distillation mechanical fallback"))
        compact.fallback = fallback_mechanical_summary(distill_these)
        print(f"Distilled fallback to {compact.fallback}")
    
    return compact 
        
