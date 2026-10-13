from typing import Tuple, Any, Optional, List
import uuid
from pydantic import BaseModel

class AgentRequest(BaseModel):
    request: str
    max_iterations: int = 150
    distill_at: int = 15000
    distill_to: int = 7000
    # ---------------------------------------------------------------------------
    # Tiered compression limits
    # ---------------------------------------------------------------------------
    # (min_age, char_limit) – age 0 is the newest iteration.
    # The tiers are intentionally simple; they can be tuned by the user.
    compression_tiers: List[Tuple[Int]] =  [(8, 300), (4, 600), (2, 1000)]
    worker_model: str = "gpt-oss:20b"
    worker_temp: float = 0.01
    distillation_model: str = "gpt-oss:20b"
    distillation_temp: float = 0.01
    base_url: str =  "http://10.42.0.192:11434/"
    execution_id: str = str(uuid.uuid4())
    verbose: bool = False    
    
class Iteration(BaseModel):
    iteration: int
    model_response: Any = None
    model_response_compressed: Any = None
    tool_call_result: Any = None
    tool_call_result_compressed: Any = None
    tool_call_fingerprint: Optional[str] = None
    result_fingerprint: Optional[str] = None
    compression_limit: Optional[int] = None
    tool_name: Optional[str] = None
    stagnant_count: int = 0


class Compaction(BaseModel):
    summary: List[dict] = []
    fallback: str = ""
    upto: int = 0          # history[:upto] is folded into summary


