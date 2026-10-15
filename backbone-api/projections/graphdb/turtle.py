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
  OR an rdflib term (URIRef/BNode/Literal) directly.
- List-valued attributes fall out of the
  same loop as scalars; no special-casing needed in build_node_turtle.
- None values are skipped, not written as empty literals.
"""
import httpx
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.term import Identifier
from typing import Callable, Literal, Optional, Tuple, Type, List, Any
from contracts.inference_contracts.info import InfoContainer
from clients.graphdb_client import post_turtle
from datetime import datetime
from pydantic import BaseModel

EX = Namespace("http://backbone-api:8000/")

def file_iri(file_location: str, identifier: str) -> URIRef:
    """Single source of truth for the file IRI convention.
    We use a deterministic URI that encodes both file_location and identifier.
    """
    return URIRef(f"{EX}file/{file_location}/{identifier}")
    

FieldMappingEntry = Tuple[str, URIRef, Optional[Callable[[object], object]]]
# (attr_name, predicate, optional transform)
# transform(value) -> either a raw python value (wrapped in Literal)
# or an rdflib Identifier (URIRef/Literal/BNode), used as-is.

FieldMapping = List[FieldMappingEntry]

def _camelcase(s: str) -> str:
    """makes lowerCamelCase from snake_case
    """
    parts = []
    for i, part in enumerate(s.split("_")):
        parts += [part.capitalize() if i > 0 else part]
    return "".join(parts)

DEFAULT_TYPE_TRANSFORMS = {
    datetime: lambda d: d.isoformat(),
    # add more if you need them
}

DEFAULT_TYPE_PREDICATE_PREFIX = {
    datetime: "",
    # add more if you need them
}

def field_mapping_from_model(
    model_cls: Type[BaseModel],
    namespace: Namespace,
    nested_path_prefix: str = "", #use when accessing nested object values eg InfoContainer sections
    default_predicate_prefix: str = "has", 
) -> FieldMapping:
    """
    Inspect *model_cls* and build the mapping build_node_turtle expects.
    overrides to default predicate or transform can be delivered in pydantic Field like:
        Field(json_schema_extra={"rdf_predicate": "isAbsurd", "rdf_transform": lambda s: str(s)})
    """
    mapping: FieldMapping = []

    for field_name, model_field in model_cls.model_fields.items():    
        t = getattr(model_field, "annotation", Any) #field type or Any
        #allow overrides to predicate or transform on class def in json_schema_extra map
        predicate = (getattr(model_field, "json_schema_extra") or {"rdf_predicate" : None}).get("rdf_predicate", None)
        
        if predicate is None:  # No override – build from the field name
            prefix = DEFAULT_TYPE_PREDICATE_PREFIX.get(t, None) 
            if prefix is None:
                prefix = default_predicate_prefix
            predicate = namespace[_camelcase(f"{prefix}{'_' if len(prefix) > 0 else ''}{field_name}")]
        else:
            predicate = namespace[predicate]
        
        transform: Optional[Callable] = (getattr(model_field, "json_schema_extra") or {"rdf_transform" : None}).get("rdf_transform", None)
        if transform is None:
            transform = DEFAULT_TYPE_TRANSFORMS.get(t, None)

        mapping.append((f"{nested_path_prefix}.{field_name}", predicate, transform))

    return mapping
    

def get_nested_attr(obj, path: str, default=None):
    for name in path.split("."):
        if obj is None:
            return default
        obj = getattr(obj, name, default)
        if obj is default:
            return default
    return obj
    
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
        if "." in attr_name:
            raw_value = get_nested_attr(entity, attr_name)
        else:
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

def object_to_turtle(
    thing: Any, 
    mapping: FieldMapping, 
    file_location: str,
    identifier: str,
    type_name: str,
    graph: Graph | None = None
) -> str:
    """Build (or extend) a Graph for one thing object given mapping and
    return its Turtle serialization. Pass an existing `graph` to batch
    multiple entities into one document/POST later; omitted, a fresh
    graph is used and this returns just that one edge node's triples.
    """
    g = graph if graph is not None else Graph()
    
    build_node_turtle(
        g,
        file_iri(file_location, identifier),
        EX[type_name],
        thing,
        mapping,
    )
    return g.serialize(format="turtle")


async def write_object_to_graphdb(
    thing: Any,
    file_location: str,
    identifier: str,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Thin wrapper: project then transport. All the actual write
    mechanics (URL, error handling, client reuse) live in
    clients.graphdb_client.post_turtle -- this function's only job is
    knowing how to project to turtle first.
    """
    if isinstance(thing, InfoContainer):
        mapping = field_mapping_from_model(thing.info, EX, "info") + field_mapping_from_model(thing.contains, EX, "contains")
        type_name = str(type(thing.contains))
    else:
        mapping = field_mapping_from_model(thing, EX) 
        type_name = str(type(thing))
        
    turtle = object_to_turtle(thing, mapping, file_location, identifier, type_name)
    await post_turtle(turtle, client=client)

