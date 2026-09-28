"""
projections/graphdb/claim_evidence_edge.py

Concrete projection: ClaimEvidenceEdge -> Turtle. Transport (the actual GraphDB POST)
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

from contracts.inference_contracts.claim_evidence_edge import ClaimEvidenceEdge
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

# --- ClaimEvidenceEdge projection -----------------------------------------------

def claim_evidence_edge_iri(evidence_id: str, claim_id: str) -> URIRef:
    """Single source of truth for the ClaimEvidenceEdge IRI convention.
    We use a deterministic URI that encodes both evidence and claim ids.
    """
    return URIRef(f"{EX}claim_evidence_edge/{evidence_id}_{claim_id}")

# Define the mapping from ClaimEvidenceEdge attributes to RDF predicates.
# We reuse predicates that already exist for Claim and Evidence where
# appropriate, and introduce a new predicate ex:hasSupport for the
# support score.
CLAIM_EVIDENCE_EDGE_FIELD_MAPPING: FieldMapping = [
    ("evidence_id", EX.hasEvidenceId, None),
    ("claim_id", EX.hasClaimId, None),
    ("support", EX.hasSupport, None),
    ("model_name", EX.hasModelName, None),
    ("observed_at", EX.observedAt, lambda dt: dt.isoformat()),
    ("retrieved_at", EX.retrievedAt, lambda dt: dt.isoformat()),
    ("schema_version", EX.hasSchemaVersion, None),
]


def claim_evidence_edge_to_turtle(
    edge: Any, graph: Graph | None = None
) -> str:
    """Build (or extend) a Graph for one ClaimEvidenceEdge object and
    return its Turtle serialization. Pass an existing `graph` to batch
    multiple entities into one document/POST later; omitted, a fresh
    graph is used and this returns just that one edge node's triples.
    """
    g = graph if graph is not None else Graph()
    node_iri = claim_evidence_edge_iri(edge.evidence_id, edge.claim_id)
    build_node_turtle(
        g,
        node_iri,
        EX.ClaimEvidenceEdge,
        edge,
        CLAIM_EVIDENCE_EDGE_FIELD_MAPPING,
    )
    return g.serialize(format="turtle")


async def write_claim_evidence_edge_to_graphdb(
    edge: ClaimEvidenceEdge,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Thin wrapper: project then transport. All the actual write
    mechanics (URL, error handling, client reuse) live in
    clients.graphdb_client.post_turtle -- this function's only job is
    knowing that ClaimEvidenceEdge needs claim_evidence_edge_to_turtle()
    first.
    """
    turtle = claim_evidence_edge_to_turtle(edge)
    await post_turtle(turtle, client=client)

"""
Quick sanity check: after creating this file, you can import the
projection and run `claim_evidence_edge_to_turtle` on a sample
ClaimEvidenceEdge instance to verify that the Turtle contains the
expected triples.
"""
