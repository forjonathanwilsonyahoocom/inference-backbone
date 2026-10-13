from pydantic import BaseModel, Field
from typing import Generic, TypeVar
from typing_extensions import Literal
from contracts.inference_contracts.validations import ArtifactId

class InfoNode(BaseModel):
    """For objects that are created by llm.with_structured_output
    these can be sent alongside with framework supplied info
    for enrichment of persisted artifacts without llm context pollution
    """
    id: ArtifactId
    execution_id: str | None #stamped by framework
    instance_number_start: int | None #stamped by framework
    instance_number_end: int | None #stamped by framework
    content_hash: str | None = None #stamped by framework

class InfoContainer(BaseModel, Generic[T]):
    info: InfoNode
    contains: T

EdgeType = Literal[
    "connects",
    "supports",
    "contradicts",
    "qualifies",
    "supersedes",
    "derived_from",
    "depends_on",
    "reports",
]

class InfoEdge(BaseModel):
    """A typed, directed relationship between graph objects."""

    id: str
    source_id: str #deliberately loose to allow connection from node OR edge
    target_id: str #deliberately loose to allow connection to node OR edge
    type: EdgeType
    context: str | None = None
    assessment_confidence: float | None = Field(default=None, ge=0, le=1)
    execution_id: str | None = None
    
