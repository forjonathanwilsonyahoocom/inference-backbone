"""
projections/graphdb/claim.py

Concrete projection: Claim -> Turtle. Transport (the actual GraphDB POST)
lives in clients/graphdb_client.py, not here -- this module only ever
builds Graph/Turtle content.

Design notes:
- field_mapping is an ordered list of (attr_name, predicate, transform)
  tuples, not a dict, so field order is stable/readable and diffable.
- transform may return a plain Python value (gets wrapped in Literal)
  OR an rdflib term (URIRef/BNode/Literal) directly -- this is how
  relational fields like parent_evidence_ids point at other nodes
  instead of being flattened into literals.
- List-valued attributes (e.g. parent_evidence_ids) fall out of the
  same loop as scalars; no special-casing needed in build_node_turtle.
- None values are skipped, not written as empty literals.
"""

from typing import Any, Callable

import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier

from contracts.inference_contracts.claim import Claim
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

# --- Claim projection -----------------------------------------------

def claim_iri(claim_id: str) -> URIRef:
    """Single source of truth for the Claim IRI convention."""
    return URIRef(f"{EX}claim/{claim_id}")

CLAIM_FIELD_MAPPING: FieldMapping = [
    ("claim_id", EX.hasClaimId, None),
    ("importance", EX.hasImportance, None),
    ("execution_id", EX.hasExecutionId, None),
    ("content", EX.hasContent, None),
    ("content_hash", EX.hasContentHash, None),
    ("observed_at", EX.observedAt, lambda dt: dt.isoformat()),
    ("retrieved_at", EX.retrievedAt, lambda dt: dt.isoformat()),
    ("embedding_model", EX.hasEmbeddingModel, None),
    ("embedding_task", EX.hasEmbeddingTask, None),
    ("validator_version", EX.hasValidatorVersion, None),
    ("schema_version", EX.hasSchemaVersion, None),
    # metadata omitted for now
]


def claim_to_turtle(claim: Any, graph: Graph | None = None) -> str:
    """Build (or extend) a Graph for one Claim object and return its
    Turtle serialization. Pass an existing `graph` to batch multiple
    entities into one document/POST later; omitted, a fresh graph is
    used and this returns just that one Claim node's triples.
    """
    g = graph if graph is not None else Graph()
    node_iri = claim_iri(claim.claim_id)
    build_node_turtle(g, node_iri, EX.Claim, claim, CLAIM_FIELD_MAPPING)
    return g.serialize(format="turtle")


async def write_claim_to_graphdb(
    claim: Claim,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Thin wrapper: project then transport. All the actual write
    mechanics (URL, error handling, client reuse) live in
    clients.graphdb_client.post_turtle -- this function's only job is
    knowing that Claim needs claim_to_turtle() first.
    """
    turtle = claim_to_turtle(claim)
    await post_turtle(turtle, client=client)
