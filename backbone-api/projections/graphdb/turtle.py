"""
projections/graphdb/turtle.py

Generalized entity -> RDF/Turtle projection,

Transport (the actual GraphDB POST)
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

EX = Namespace("http://mindbodyengineer.com/")

# (attr_name, predicate, optional transform)
# transform(value) -> either a raw python value (wrapped in Literal)
# or an rdflib Identifier (URIRef/Literal/BNode), used as-is.
FieldMapping = list[tuple[str, URIRef, Callable[[Any], Any] | None]]


def build_node_turtle(
    graph: Graph,
    node_iri: URIRef,
    rdf_type: URIRef,
    entity: Any,
    field_mapping: FieldMapping,
) -> Graph:
    """Add triples for one entity to `graph` per field_mapping. Mutates
    and returns `graph` so callers can build up multi-node graphs."""
    graph.add((node_iri, RDF.type, rdf_type))

    for attr_name, predicate, transform in field_mapping:
        raw_value = getattr(entity, attr_name, None)
        if raw_value is None:
            continue

        values = raw_value if isinstance(raw_value, list) else [raw_value]
        for v in values:
            if v is None:
                continue
            transformed = transform(v) if transform else v
            term = (
                transformed
                if isinstance(transformed, Identifier)
                else Literal(transformed)
            )
            graph.add((node_iri, predicate, term))

    return graph


