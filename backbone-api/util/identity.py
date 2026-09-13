import uuid

def context_based_id(content: str) -> str:
    """Return a deterministic UUID5 string based on *content*.

    The spec requires a *stable* identifier for each artifact.
    Using :func:`uuid.uuid5` with a fixed namespace guarantees that
    the same content always maps to the same UUID, while still keeping
    the identifier opaque.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, content))

