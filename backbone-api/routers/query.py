from fastapi import APIRouter, Query
from rdflib.plugins.sparql.parser import parseQuery
from pyparsing import ParseBaseException
import httpx
import os

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/inference-backbone")

query_router = APIRouter()

def require_read_query(sparql: str) -> str:
    """Return a SPARQL read query, or raise ValueError for invalid/update input."""
    try:
        parseQuery(sparql)  # Accepts SPARQL query forms; rejects update operations.
    except (ParseBaseException, TypeError) as exc:
        raise ValueError("Only valid SPARQL read queries are allowed") from exc

    return sparql

@query_router.get("/sparql")
async def sparql(query: str = Query(..., description="SPARQL query")):

    query = require_read_query(query)
    
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPHDB_URL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
    r.raise_for_status()
    
    return r.json()
