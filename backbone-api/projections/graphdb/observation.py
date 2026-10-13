from typing import Any, Callable

import hashlib
import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.agent_state import Observation
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

# deterministic hash helper for generating IRIs when no explicit id is present

def _hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

# IRI convention for Observation

def observation_iri(statement: str, source: str) -> URIRef:
    """Return deterministic IRI for an Observation.
    Uses a short hash of statement+source to keep the IRI stable.
    """
    key = f"{statement}|{source}"
    return URIRef(f"{EX}file/observation/{_hash_str(key)}")

OBSERVATION_FIELD_MAPPING: FieldMapping = [
    ("statement", EX.hasStatement, None),
    ("source", EX.hasSource, None),
    ("confidence", EX.hasConfidence, None),
]


def observation_to_turtle(obs: Observation, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = observation_iri(obs.statement, obs.source)
    build_node_turtle(g, node_iri, EX.Observation, obs, OBSERVATION_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_observation_to_graphdb(obs: Observation, client: httpx.AsyncClient | None = None) -> None:
    turtle = observation_to_turtle(obs)
    await post_turtle(turtle, client=client)
