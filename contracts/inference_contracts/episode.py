from typing import Literal
from pydantic import BaseModel, Field

class Episode(BaseModel):
    mission: str = Field(
        description="What the agent was trying to accomplish."
    )

    outcome: Literal[
        "success",
        "partial_success",
        "failure",
        "unknown",
    ] = Field(
        description="The best-supported outcome of the mission."
    )

    significant_events: list[str] = Field(
        description=(
            "Important actions, results, obstacles, and state changes "
            "that characterized this execution."
        )
    )

    findings: list[str] = Field(
        description=(
            "Useful information discovered during the execution "
            "that may be relevant to future tasks."
        )
    )

    lessons: list[str] = Field(
        description=(
            "Potentially reusable lessons supported by the execution. "
            "Use an empty list when no clear lesson is supported."
        )
    )

    unresolved_questions: list[str] = Field(
        description=(
            "Important uncertainties or unresolved issues. "
            "Do not invent explanations for observed failures."
        )
    )

    evidence_refs: list[str] = Field(
        description=(
            "Identifiers of source trace events explicitly referenced "
            "in the supplied summary."
        )
    )
