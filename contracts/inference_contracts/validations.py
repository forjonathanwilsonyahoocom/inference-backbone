import re
from uuid import UUID

from pydantic import AfterValidator
from typing import Annotated


def validate_artifact_id(value: str) -> str:
    uuid_part, separator, iteration_part = value.rpartition("-")

    if not separator or not iteration_part.isdecimal():
        raise ValueError(
            "Artifact ID must have the format <UUID4>-<iteration#>"
        )

    try:
        parsed_uuid = UUID(uuid_part)
    except ValueError as exc:
        raise ValueError("Artifact ID must contain a valid UUID4") from exc

    if parsed_uuid.version != 4:
        raise ValueError("Artifact ID must contain a UUID4")

    return value


ArtifactId = Annotated[str, AfterValidator(validate_artifact_id)]
