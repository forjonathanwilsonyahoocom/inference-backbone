from typing import Any, Callable

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.final_answer import FinalAnswer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

FINAL_ANSWER_FIELD_MAPPING: FieldMapping = [
    ("final_answer_id", EX.hasFinalAnswerId, None),
    ("execution_id", EX.hasExecutionId, None),
    ("instance_number", EX.hasInstanceNumber, None),
    ("content", EX.hasContent, None),
    ("content_hash", EX.hasContentHash, None),
]


def final_answer_to_turtle(ans: FinalAnswer, graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/final_answer/{ans.final_answer_id}")
    build_node_turtle(g, node_iri, EX.FinalAnswer, ans, FINAL_ANSWER_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_final_answer_to_graphdb(ans: FinalAnswer, client: httpx.AsyncClient | None = None) -> None:
    turtle = final_answer_to_turtle(ans)
    await post_turtle(turtle, client=client)
