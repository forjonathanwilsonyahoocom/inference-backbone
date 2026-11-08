from typing import Optional, List, Tuple
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# 1) Scaffold – full shape, but only request & base_url are required
#    Every other field is Optional (defaults to None)
# ---------------------------------------------------------------------------
class AgentRequest(BaseModel):
    request: str                    # ← required
    base_url: str                   # ← required
    mode: str                       # ← required
    system_message: Optional[str] = None
    execution_id: Optional[str] = None
    max_iterations: Optional[int] = None
    distill_at: Optional[int] = None
    distill_to: Optional[int] = None
    compression_tiers: Optional[List[Tuple[int, int]]] = None
    compression_adjust_by_utility: Optional[float] = None
    worker_model: Optional[str] = None
    worker_temp: Optional[float] = None
    worker_num_ctx: Optional[int] = None
    distillation_model: Optional[str] = None
    distillation_temp: Optional[float] = None
    distillation_num_ctx: Optional[int] = None
    distillation_delta_model: Optional[str] = None
    verbose: Optional[bool] = None

