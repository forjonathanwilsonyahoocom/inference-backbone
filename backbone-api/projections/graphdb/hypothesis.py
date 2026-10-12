from typing import Any, Callable

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.agent_state import Hypothesis
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

HYPOTHESIS_FIELD_MAPPING: FieldMapping = [
    ("hypothesis", EX.hasHypothesis, None),
    ("status", EX.hasStatus, None),
    ("confidence", EX.hasConfidence, None),
]


def hypothesis_to_turtle(hyp: Hypothesis, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/hypothesis/{hyp.hypothesis}")
    build_node_turtle(g, node_iri, EX.Hypothesis, hyp, HYPOTHESIS_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_hypothesis_to_graphdb(hyp: Hypothesis, client: httpx.AsyncClient | None = None) -> None:
    turtle = hypothesis_to_turtle(hyp)
    await post_turtle(turtle, client=client)
