"""
clients/graphdb_client.py

Generic GraphDB write client. Knows nothing about Evidence, Claim, or
any other entity -- just POSTs Turtle strings to the repository's
/statements endpoint. Entity-specific wrappers (write_evidence_to_graphdb,
write_claim_to_graphdb, ...) live next to their projections and call
post_turtle() here.
"""

import os

import httpx

# e.g. http://graphdb:7200/repositories/inference-backbone
GRAPHDB_URL = os.environ["GRAPHDB_URL"]


class GraphDBWriteError(RuntimeError):
    """Raised when GraphDB rejects or fails to accept a Turtle write.
    Kept as its own type (rather than letting httpx.HTTPStatusError
    propagate) so callers can catch this specifically and decide
    whether a GraphDB failure should fail the whole request or just
    be logged -- that policy is a per-route decision, not this
    client's concern."""


async def post_turtle(
    turtle: str,
    client: httpx.AsyncClient | None = None,
) -> None:
    """POST a Turtle document to GraphDB's /statements endpoint.
    Raises GraphDBWriteError on any non-2xx response or request
    failure.

    Accepts an optional shared `client` so an app can reuse one
    httpx.AsyncClient (e.g. via FastAPI lifespan) across requests
    instead of opening a new connection per call; if omitted, a
    short-lived client is used.
    """
    url = f"{GRAPHDB_URL}/statements"
    headers = {"Content-Type": "text/turtle"}

    async def _post(c: httpx.AsyncClient) -> None:
        try:
            response = await c.post(url, content=turtle, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GraphDBWriteError(f"GraphDB write failed: {exc}") from exc

    if client is not None:
        await _post(client)
    else:
        async with httpx.AsyncClient(timeout=10.0) as c:
            await _post(c)
