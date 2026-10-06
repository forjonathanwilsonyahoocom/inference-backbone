from typing import Any, Optional, List
from pydantic import BaseModel

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


