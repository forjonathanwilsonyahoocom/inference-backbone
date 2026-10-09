import re

from typing import Annotated
from pydantic import AfterValidator


_ARTIFACT_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"4[0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-"
    r"[0-9a-fA-F]{12}"
    r"-(0|[1-9][0-9]*)$"
)


def validate_artifact_id(value: str) -> str:
    if not _ARTIFACT_ID_PATTERN.fullmatch(value):
        raise ValueError("Expected UUID4-iteration identifier")
    return value


ArtifactId = Annotated[str, AfterValidator(validate_artifact_id)]
