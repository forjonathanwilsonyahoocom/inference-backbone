"""
projections/graphdb/evidence.py

concrete projection: Evidence -> Turtle. Transport (the actual GraphDB POST)
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

from contracts.inference_contracts.evidence import Evidence
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

# --- Evidence projection -----------------------------------------------

def evidence_iri(evidence_id: str) -> URIRef:
    """Single source of truth for the Evidence IRI convention, since
    parent_evidence_ids also needs to build IRIs for other Evidence
    nodes, not just the node currently being written."""
    return URIRef(f"{EX}evidence/{evidence_id}")


EVIDENCE_FIELD_MAPPING: FieldMapping = [
    ("evidence_id", EX.hasEvidenceId, None),
    ("execution_id", EX.hasExecutionId, None),
    ("event_id", EX.hasEventId, None),
    ("evidence_type", EX.hasEvidenceType, None),
    ("content", EX.hasContent, None),
    ("content_hash", EX.hasContentHash, None),
    ("source_type", EX.hasSourceType, None),
    ("source_name", EX.hasSourceName, None),
    ("source_url", EX.hasSourceUrl, None),
    ("observed_at", EX.observedAt, lambda dt: dt.isoformat()),
    ("retrieved_at", EX.retrievedAt, lambda dt: dt.isoformat()),
    ("extraction_method", EX.hasExtractionMethod, None),
    # relation, not a literal -- points at another Evidence node
    ("parent_evidence_ids", EX.hasParentEvidence, evidence_iri),
    ("worker_version", EX.hasWorkerVersion, None),
    ("schema_version", EX.hasSchemaVersion, None),
    # metadata (dict[str, Any]) intentionally omitted for v1 -- no
    # agreed triples-per-key scheme yet, still under discussion.
]


def evidence_to_turtle(evidence: Any, graph: Graph | None = None) -> str:
    """Build (or extend) a Graph for one Evidence object and return its
    Turtle serialization. Pass an existing `graph` to batch multiple
    entities into one document/POST later; omitted, a fresh graph is
    used and this returns just that one Evidence node's triples.

    Assumes `evidence.content_hash` is already populated by the caller
    (the route hashes content before calling this) -- if it's still
    None here, that field is silently skipped, not an error.
    """
    g = graph if graph is not None else Graph()
    node_iri = evidence_iri(evidence.evidence_id)
    build_node_turtle(g, node_iri, EX.Evidence, evidence, EVIDENCE_FIELD_MAPPING)
    return g.serialize(format="turtle")


async def write_evidence_to_graphdb(
    evidence: Evidence,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Thin wrapper: project then transport. All the actual write
    mechanics (URL, error handling, client reuse) live in
    clients.graphdb_client.post_turtle -- this function's only job is
    knowing that Evidence needs evidence_to_turtle() first.
    write_claim_to_graphdb, when Claims land, will look identical
    except for the projection call.
    """
    turtle = evidence_to_turtle(evidence)
    await post_turtle(turtle, client=client)
