import httpx
from rdflib import Graph, URIRef

from contracts.inference_contracts.agent_state import Artifact
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

from projections.graphdb.info import INFO_FIELD_MAPPING

ARTIFACT_FIELD_MAPPING: FieldMapping = INFO_FIELD_MAPPING + [
    ("contains.id", EX.hasArtifactId, None),
    ("contains.type", EX.hasArtifactType, None),
    ("contains.value", EX.hasArtifactValue, None),
]

def artifact_to_turtle(artifact: InfoContainer[Artifact], graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/agent_state/{artifact.info.source_id}")
    build_node_turtle(g, node_iri, EX.Artifact, artifact, ARTIFACT_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_artifact_to_graphdb(artifact: InfoContainer[Artifact], client: httpx.AsyncClient | None = None) -> None:
    turtle = artifact_to_turtle(artifact)
    await post_turtle(turtle, client=client)
