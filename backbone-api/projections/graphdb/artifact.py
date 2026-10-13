from typing import Any

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.agent_state import Artifact
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

import hashlib

# deterministic hash helper for generating IRIs when no explicit id is present

def _hash(*args: Any) -> str:
    return hashlib.sha256("||".join(map(str, args)).encode()).hexdigest()[:16]

# IRI convention for Artifact

def artifact_iri(artifact_id: str) -> URIRef:
    return URIRef(f"{EX}file/artifact/{artifact_id}")

ARTIFACT_FIELD_MAPPING: FieldMapping = [
    ("id", EX.hasArtifactId, None),
    ("type", EX.hasArtifactType, None),
    ("value", EX.hasArtifactValue, None),
]


def artifact_to_turtle(artifact: Artifact, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = artifact_iri(artifact.id)
    build_node_turtle(g, node_iri, EX.Artifact, artifact, ARTIFACT_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_artifact_to_graphdb(artifact: Artifact, client: httpx.AsyncClient | None = None) -> None:
    turtle = artifact_to_turtle(artifact)
    await post_turtle(turtle, client=client)
