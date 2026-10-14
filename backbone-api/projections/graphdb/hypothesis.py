import httpx
from rdflib import Graph, URIRef
from contracts.inference_contracts.agent_state import Hypothesis
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX
from projections.graphdb.info import INFO_FIELD_MAPPING

HYPOTHESIS_FIELD_MAPPING: FieldMapping = INFO_FIELD_MAPPING + [
    ("contains.hypothesis", EX.hasHypothesis, None),
    ("contains.status", EX.hasStatus, None),
    ("contains.confidence", EX.hasConfidence, None),
]

def hypothesis_to_turtle(hyp: InfoContainer[Hypothesis], graph: Graph | None = None) -> str:
    g = graph if graph is not None else Graph()
    node_iri = URIRef(f"{EX}file/agent_state/{hyp.info.source_id}")
    build_node_turtle(g, node_iri, EX.Hypothesis, hyp, HYPOTHESIS_FIELD_MAPPING)
    return g.serialize(format="turtle")

async def write_hypothesis_to_graphdb(hyp: InfoContainer[Hypothesis], client: httpx.AsyncClient | None = None) -> None:
    turtle = hypothesis_to_turtle(hyp)
    await post_turtle(turtle, client=client)
