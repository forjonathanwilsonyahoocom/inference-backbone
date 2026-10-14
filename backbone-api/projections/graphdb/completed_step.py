import httpx
from rdflib import Graph, URIRef
from contracts.inference_contracts.agent_state import CompletedStep
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX
from projections.graphdb.info import INFO_FIELD_MAPPING

COMPLETED_STEP_FIELD_MAPPING: FieldMapping = INFO_FIELD_MAPPING + [
    ("contains.step", EX.hasStep, None),
    ("contains.result", EX.hasResult, None),
]

def completed_step_to_turtle(step: InfoContainer[CompletedStep], graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/agent_state/{step.info.source_id}")
    build_node_turtle(g, node_iri, EX.CompletedStep, step, COMPLETED_STEP_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_completed_step_to_graphdb(step: InfoContainer[CompletedStep], client: httpx.AsyncClient | None = None) -> None:
    turtle = completed_step_to_turtle(step)
    await post_turtle(turtle, client=client)
