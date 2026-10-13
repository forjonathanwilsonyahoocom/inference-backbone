from typing import Any, Callable

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.agent_state import Understanding
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

UNDERSTANDING_FIELD_MAPPING: FieldMapping = [
    ("concept", EX.hasConcept, None),
    ("detail", EX.hasDetail, None),
]


def understanding_to_turtle(understanding: Understanding, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/understanding/{understanding.concept}")
    build_node_turtle(g, node_iri, EX.Understanding, understanding, UNDERSTANDING_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_understanding_to_graphdb(understanding: Understanding, client: httpx.AsyncClient | None = None) -> None:
    turtle = understanding_to_turtle(understanding)
    await post_turtle(turtle, client=client)
