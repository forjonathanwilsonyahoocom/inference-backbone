# FastAPI app to proxy SPARQL queries to GraphDB
from fastapi import FastAPI, Query, Request
import httpx
import os
import requests
import json

## 4️⃣  Integrating with the local LLM (Ollama)
app = FastAPI()
OLLAMA_URL = "http://10.42.0.192:11434/api/chat"

@app.post("/ask")
async def ask(request: Request):
    body = await request.json()
    user_question = body["question"]

    # Pull inference‑context (e.g., latest experiment results)
    sparql = """
    PREFIX ex: <http://example.org/>
    SELECT ?exp ?value
    WHERE {
      ?exp a ex:Experiment ;
           ex:hasResult ?res .
      ?res ex:resultValue ?value .
    }
    """
    sparql_resp = requests.post(
        "http://graphdb:8080/repositories/example/sparql",
        data={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
    )
    results = sparql_resp.json()["results"]["bindings"]
    context = "\n".join([f"Experiment {r['exp']['value']}: {r['value']['value']}" for r in results])

    prompt = f"{context}\n\nQuestion: {user_question}\nAnswer:"
    ollama_resp = requests.post(OLLAMA_URL, json={"model": "llama3", "messages": [{"role":"user","content":prompt}]})
    return json.loads(ollama_resp.content)

GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/inference-backbone")

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
