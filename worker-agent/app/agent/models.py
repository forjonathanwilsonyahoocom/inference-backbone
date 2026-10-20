from typing import Tuple, Any, Optional, List, Dict
import uuid
from pydantic import BaseModel

class AgentRequest(BaseModel):
    request: str #instruction for agent action
    base_url: str #send your local ollama server base url
    execution_id: str = str(uuid.uuid4()) # unique per run
    max_iterations: int = 150 #intentionally unbounded, run forever at your own risk
    distill_at: int = 15000 #token budget before distillation, intentionally unbounded for experimentation sake
    distill_to: int = 7000 #token target after distillation, intentionally unbounded for experimentation sake
    # ---------------------------------------------------------------------------
    # Tiered compression limits
    # ---------------------------------------------------------------------------
    # (min_age, char_limit) – age 0 is the newest iteration.
    # The tiers are intentionally simple; they can be tuned by the user.
    compression_tiers: List[Tuple[int, int]] =  [(8, 300), (4, 600), (2, 1000)] 
    worker_model: str = "gpt-oss:20b"
    worker_temp: float = 0.01  #intentionally unbounded for experimentation sake
    worker_num_ctx: int = 40960  #intentionally unbounded for experimentation sake
    distillation_model: str = "gpt-oss:20b"
    distillation_temp: float = 0.01  #intentionally unbounded for experimentation sake
    distillation_num_ctx: int = 40960  #intentionally unbounded for experimentation sake
    verbose: bool = False    
    
class Iteration(BaseModel):
    iteration: int
    model_response: Any = None
    model_response_compressed: Any = None
    model_response_instance_number: int = None
    tool_call_result: Any = None
    tool_call_result_instance_number: int = None
    tool_call_result_compressed: Any = None
    tool_call_result_chunks: List[Dict] = None
    tool_call_fingerprint: Optional[str] = None
    result_fingerprint: Optional[str] = None
    compression_limit: Optional[int] = None
    tool_name: Optional[str] = None
    stagnant_count: int = 0


class Compaction(BaseModel):
    summary: List[dict] = []
    fallback: str = ""  # only holds a mechanically extracted string when llm call fails multiple times
    upto: int = 0       # history[:upto] is folded into summary


