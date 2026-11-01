from typing import List

from pydantic import BaseModel, Field


class ExtractionClaim(BaseModel):
    """A single discrete, checkable factual claim extracted from an agent's
    final response.

    This is a lightweight prompting contract: the validator only needs the
    claim text and how important it is. The persistence layer (``Claim``)
    enriches this with ids, hashes, timestamps, etc.
    """

    text: str
    importance: float = Field(
        ge=0.0,
        le=1.0,
        description="Importance of the claim on a scale from 0.0 (marginal) to 1.0 (very important).",
    )


class ExtractionResult(BaseModel):
    """The full output of the claim-extraction phase: a list of claims."""

    claims: List[ExtractionClaim]
