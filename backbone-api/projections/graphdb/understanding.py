import httpx
from rdflib import Graph, URIRef

from contracts.inference_contracts.agent_state import Understanding
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX
from projections.graphdb.info import INFO_FIELD_MAPPING

UNDERSTANDING_FIELD_MAPPING: FieldMapping = INFO_FIELD_MAPPING + [
    ("contains.concept", EX.hasConcept, None),
    ("contains.detail", EX.hasDetail, None),
]

def understanding_to_turtle(understanding: InfoContainer[Understanding], graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/agent_state/{understanding.info.source_id}")
    build_node_turtle(g, node_iri, EX.Understanding, understanding, UNDERSTANDING_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_understanding_to_graphdb(understanding: InfoContainer[Understanding], client: httpx.AsyncClient | None = None) -> None:
    turtle = understanding_to_turtle(understanding)
    await post_turtle(turtle, client=client)
