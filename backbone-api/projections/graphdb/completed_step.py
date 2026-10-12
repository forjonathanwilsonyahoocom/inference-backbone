from typing import Any, Callable

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.agent_state import CompletedStep
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

COMPLETED_STEP_FIELD_MAPPING: FieldMapping = [
    ("step", EX.hasStep, None),
    ("result", EX.hasResult, None),
]


def completed_step_to_turtle(step: CompletedStep, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/completed_step/{step.step}")
    build_node_turtle(g, node_iri, EX.CompletedStep, step, COMPLETED_STEP_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_completed_step_to_graphdb(step: CompletedStep, client: httpx.AsyncClient | None = None) -> None:
    turtle = completed_step_to_turtle(step)
    await post_turtle(turtle, client=client)
