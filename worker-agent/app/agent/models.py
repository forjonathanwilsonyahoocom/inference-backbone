from typing import Tuple, Any, Optional, List, Dict
import uuid
from pydantic import BaseModel
from contracts.inference_contracts.agent_state_delta import DistillationDelta
from contracts.inference_contracts.worker_agent_request import AgentRequest
from prompts.worker import DEFAULT_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# 2) Materialization – replace every None with the implementation default
# ---------------------------------------------------------------------------
def materialize_agent_request(scaffold: AgentRequest) -> AgentRequest:
    return AgentRequest(
        request=scaffold.request,
        base_url=scaffold.base_url,
        system_message=scaffold.system_message if scaffold.system_message is not None else DEFAULT_SYSTEM_PROMPT,
        execution_id=scaffold.execution_id if scaffold.execution_id is not None else str(uuid.uuid4()),
        max_iterations=scaffold.max_iterations if scaffold.max_iterations is not None else 150,
        distill_at=scaffold.distill_at if scaffold.distill_at is not None else 15_000,
        distill_to=scaffold.distill_to if scaffold.distill_to is not None else 7_000,
        compression_tiers=scaffold.compression_tiers if scaffold.compression_tiers is not None else [(8, 300), (4, 600), (2, 1000)],
        compression_adjust_by_utility=scaffold.compression_adjust_by_utility if scaffold.compression_adjust_by_utility is not None else 1.2,
        worker_model=scaffold.worker_model if scaffold.worker_model is not None else "gpt-oss:20b",
        worker_temp=scaffold.worker_temp if scaffold.worker_temp is not None else 0.01,
        worker_num_ctx=scaffold.worker_num_ctx if scaffold.worker_num_ctx is not None else 40_960,
        distillation_model=scaffold.distillation_model if scaffold.distillation_model is not None else "gpt-oss:20b",
        distillation_temp=scaffold.distillation_temp if scaffold.distillation_temp is not None else 0.01,
        distillation_num_ctx=scaffold.distillation_num_ctx if scaffold.distillation_num_ctx is not None else 40_960,
        distillation_delta_model=scaffold.distillation_delta_model if scaffold.distillation_delta_model is not None else "gpt-oss:20b",
        verbose=scaffold.verbose if scaffold.verbose is not None else False,
    )

    
class Iteration(BaseModel):
    iteration: int
    model_response: Any = None
    model_response_compressed: Any = None
    model_response_instance_number: int = None
    tool_call_result: Any = None
    tool_call_result_instance_number: int = None
    tool_call_result_compressed: Any = None
    tool_call_result_chunks: List[Dict] = None
    tool_call_result_chunk_query: str = None
    tool_call_result_utility: float = None
    tool_call_fingerprint: Optional[str] = None
    result_fingerprint: Optional[str] = None
    compression_limit: Optional[int] = None
    tool_name: Optional[str] = None
    stagnant_count: int = 0
    is_silenced: bool = False #set to remove from context


class Compaction(BaseModel):
    summary: List[dict] = [] #holds the progressive original agent state objects
    summary_deltas: List[DistillationDelta] = [] #holds the list of delta update from the summary_aggregate to the latest summary
    summary_aggregate: dict = {} #holds the latest aggregation of the summary list, this is presented to the llm
    fallback: str = ""  # only holds a mechanically extracted string when llm call fails multiple times
    upto: int = 0       # history[:upto] is folded into summary


