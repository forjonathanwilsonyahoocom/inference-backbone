# FastAPI app to proxy SPARQL queries to GraphDB
from fastapi import FastAPI, Query
import httpx
import os

app = FastAPI()

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/example")

@app.get("/sparql")
async def sparql(query: str = Query(..., description="SPARQL query")):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPHDB_URL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
    r.raise_for_status()
    return r.json()

# Simple health check
@app.get("/health")
async def health():
    return {"status": "ok"}
