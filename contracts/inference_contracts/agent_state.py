# schema_v2.py
from __future__ import annotations

from typing import Any, List
from pydantic import BaseModel, field_validator
from typing_extensions import Literal
from contracts.inference_contracts.validations import ArtifactId

# --------------------------------------------------------------------------- #
# 1️⃣  Artifact
# --------------------------------------------------------------------------- #
ArtifactType = Literal["file", "web_fetch", "llm_intent"]


class Artifact(BaseModel):
    """Represents a useful fragment of a tool’s output."""
    id: str
    type: ArtifactType
    value: str

    @field_validator("id", "value")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v


# --------------------------------------------------------------------------- #
# 2️⃣  Claim
# --------------------------------------------------------------------------- #
class Claim(BaseModel):
    statement: str
    source: str
    confidence: float

    @field_validator("statement", "source")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("confidence")
    @classmethod
    def in_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return v


# --------------------------------------------------------------------------- #
# 3️⃣  Understanding
# --------------------------------------------------------------------------- #
class Understanding(BaseModel):
    concept: str
    detail: str


# --------------------------------------------------------------------------- #
# 4️⃣  Hypothesis
# --------------------------------------------------------------------------- #
HypothesisStatus = Literal["pending", "confirmed", "ruled‑out"]


class Hypothesis(BaseModel):
    hypothesis: str
    status: HypothesisStatus
    confidence: float

    @field_validator("confidence")
    @classmethod
    def in_range(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("confidence must be between 0 and 1")
        return v


# --------------------------------------------------------------------------- #
# 5️⃣  Completed Step
# --------------------------------------------------------------------------- #
class CompletedStep(BaseModel):
    step: str
    result: str


# --------------------------------------------------------------------------- #
# 6️⃣  Root Model – the overall “state” container
# --------------------------------------------------------------------------- #
class AgentState(BaseModel):
    """
    A container for the various artifacts the agent has produced.
    """
    state_id: ArtifactId | None #stamped by framework
    execution_id: str | None #stamped by framework
    instance_number: int | None #stamped by framework
    content_hash: str | None = None #stamped by framework
    
    artifacts: List[Artifact] = []
    claims: List[Claim] = []
    understandings: List[Understanding] = []
    hypotheses: List[Hypothesis] = []
    completed_steps: List[CompletedStep] = []

    # ---- before‑mode list coercion ---------------------------------------
    @field_validator(
        "artifacts",
        "claims",
        "understandings",
        "hypotheses",
        "completed_steps",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, v: Any) -> List[Any]:
        """
        If a single dict (or even a single primitive) is supplied, wrap it in
        a list so that the normal validators get a list to work on.
        """
        if isinstance(v, list):
            return v
        # Special case: a string, int, etc. – just wrap it
        return [v]


# --------------------------------------------------------------------------- #
# 7️⃣  Quick sanity‑check
# --------------------------------------------------------------------------- #
def test_state_object():
     # Single artifact dict – gets wrapped into a list automatically
     state = AgentState(
         artifacts={"id": "a1", "type": "file", "value": "def foo(): pass"},
         claims=[
             {"statement": "The file contains a function",
              "source": "a1",
              "confidence": 0.95}
         ],
         understandings=[{"concept": "Python function",
                          "detail": "Simple function definition."}],
         hypotheses=[{"hypothesis": "The function does something",
                       "status": "pending",
                       "confidence": 0.5}],
         completed_steps=[{"step": "Load file",
                           "result": "Read a1 successfully."}]
     )
     print(state.json(indent=2))

