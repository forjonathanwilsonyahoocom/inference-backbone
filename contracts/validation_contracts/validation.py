from typing import Dict

from pydantic import BaseModel, Field


class SupportEntry(BaseModel):
    """Per-evidence support rating for a single claim.

    Mirrors the prompt's nested object shape: ``{"supported": <float>}``.
    The float is the degree to which the evidence item supports the claim,
    where 1.0 means fully supported and 0.0 means unrelated.
    """

    supported: float = Field(
        ge=0.0,
        le=1.0,
        description="Degree to which the evidence item supports the claim (0.0 = unrelated, 1.0 = fully supported).",
    )


class ValidationResult(BaseModel):
    """The full output of the validation phase.

    ``support_map`` is keyed by claim id (taken from the input claims list)
    and maps each evidence id to its support rating. This matches the shape
    consumed downstream by ``link_claims_to_evidence``.
    """

    support_map: Dict[str, SupportEntry] = Field(
        default_factory=dict,
        description="Map of claim_id -> {evidence_id: SupportEntry} support ratings.",
    )
