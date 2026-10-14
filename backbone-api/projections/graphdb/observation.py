import httpx
from rdflib import Graph, URIRef

from contracts.inference_contracts.agent_state import Observation
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX
from projections.graphdb.info import INFO_FIELD_MAPPING

OBSERVATION_FIELD_MAPPING: FieldMapping = INFO_FIELD_MAPPING + [
    ("contains.statement", EX.hasStatement, None),
    ("contains.source", EX.hasSource, None),
    ("contains.confidence", EX.hasConfidence, None),
]

def observation_to_turtle(obs: InfoContainer[Observation], graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/agent_state/{obs.info.source_id}")
    build_node_turtle(g, node_iri, EX.Observation, obs, OBSERVATION_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_observation_to_graphdb(obs: InfoContainer[Observation], client: httpx.AsyncClient | None = None) -> None:
    turtle = observation_to_turtle(obs)
    await post_turtle(turtle, client=client)
