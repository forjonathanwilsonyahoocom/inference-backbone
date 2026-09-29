from fastapi import APIRouter, Query
import httpx
import os

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/inference-backbone")

query_router = APIRouter()

@query_router.get("/sparql")
async def sparql(query: str = Query(..., description="SPARQL query")):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPHDB_URL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
    r.raise_for_status()
    
    return r.json()
