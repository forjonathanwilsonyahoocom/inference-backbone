from typing import Dict, Any, List
from observability.metrics import MetricsWrapper
from agent.models import Compaction
from prompts.distillation import DISTILLATION_PROMPT
from contracts.inference_contracts.agent_state import AgentState
from agent.telemetry import ingest_agent_state
from langchain_ollama import ChatOllama
import json

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage
)

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

def get_distillation(metrics: MetricsWrapper, 
                     distillation_llm: ChatOllama, 
                     compact: Compaction,
                     upto: int,
                     distill_these: List[Any]) -> Compaction:
    print("Starting distill")
    
    conv_text = distillation_assembly(distill_these)
    
    distillation_messages = [
        SystemMessage(content=DISTILLATION_PROMPT),
        HumanMessage(content=conv_text),
    ]
    facts = None
    for _ in range(3):
        facts_json = None
        try:
            agent_state_facts = distillation_llm.invoke(distillation_messages)
            if not isinstance(agent_state_facts, AgentState):
                raise ValueError(f"expected a AgentState object, got {type(agent_state_facts).__name__}")
            agent_state_facts.execution_id = compact.execution_id
            agent_state_facts.instance_number = upto
            ingest_agent_state(agent_state_facts)
            facts_dict = agent_state_facts.model_dump()
            if not isinstance(facts_dict, dict):
                raise ValueError(f"expected a dict from AgentState.model_dump(), got {type(facts_dict).__name__}")
            facts = facts_dict
            metrics.emit(metrics.get_counter_message("distillation_success", "distillation agent worked"))
            break
        except Exception as exc:
            metrics.emit(metrics.get_counter_message("distillation_failure", "distillation agent crashes"))
            raw_content = str(agent_state_facts) if agent_state_facts else "(no response)"
            print(f"Distillation JSON parse failed: {exc}")
            print(f"Raw model output (truncated): {raw_content[:300]}")

    print(f"Distilled: {facts}")

    if facts is not None:
        compact.upto = upto
        compact.summary.append(facts)
        compact.fallback = ""
    else:
        metrics.emit(metrics.get_counter_message("distillation_fallback", "distillation mechanical fallback"))
        compact.fallback = fallback_mechanical_summary(distill_these)
    
    print(compact.fallback)
    
    return compact 
        
