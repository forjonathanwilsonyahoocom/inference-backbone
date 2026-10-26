from pydantic import BaseModel, Field
from typing import Literal

class RunRequest(BaseModel):
    nocache: bool = False
    workspace: str
    runtime: Literal["python", "node", "go", "rust", "php", "ast", "text"]
    command: list[str] = Field(min_length=1, max_length=32)
    timeout_seconds: int = Field(default=300, ge=1, le=900)

class RunResponse(BaseModel):
    exit_code: int | None
    timed_out: bool
    logs: str

