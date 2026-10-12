from typing import Any

from contracts.inference_contracts.task import Task
from clients.graphdb_client import post_turtle
from projections.graphdb.turtle import build_node_turtle, FieldMapping, EX

# IRI convention for Task

def task_iri(task_id: str) -> Any:
    """Return the deterministic IRI for a Task."""
    return EX[f"file/task/{task_id}"]

# Mapping of Task attributes to RDF predicates
TASK_FIELD_MAPPING: FieldMapping = [
    ("task_id", EX.hasTaskId, None),
    ("execution_id", EX.hasExecutionId, None),
    ("instance_number", EX.hasInstanceNumber, None),
    ("content", EX.hasContent, None),
    ("content_hash", EX.hasContentHash, None),
    ("model_name", EX.hasModelName, None),
    ("observed_at", EX.observedAt, lambda dt: dt.isoformat()),
]


def task_to_turtle(task: Task, graph: Any | None = None) -> str:
    """Build (or extend) a Graph for one Task object."""
    if graph is None:
        from rdflib import Graph
        graph = Graph()
    node_iri = task_iri(task.task_id)
    build_node_turtle(graph, node_iri, EX.Task, task, TASK_FIELD_MAPPING)
    return graph.serialize(format="turtle")


def write_to_graphdb(task: Task) -> Any:
    """Post the Turtle representation of a Task to GraphDB."""
    return post_turtle(task_to_turtle(task))
