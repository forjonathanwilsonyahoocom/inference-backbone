# Backbone API

The **Backbone API** is a thin FastAPI wrapper that exposes utilities for persisting inference artifacts to a GraphDB (RDF) store and a Weaviate vector database. It is used by the worker and validator agents to store the results of their runs.

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/ingest_episode` | POST | Persist an `Episode` to GraphDB and Weaviate. |
| `/ingest_claim` | POST | Persist a `Claim` to GraphDB and Weaviate. |
| `/ingest_evidence` | POST | Persist an `Evidence` to GraphDB and Weaviate. |
| `/ingest_task` | POST | Persist a `Task` to GraphDB and Weaviate. |
| `/ingest_final_answer` | POST | Persist a `FinalAnswer` to GraphDB and Weaviate. |
| `/ingest_agent_state_delta` | POST | Persist an `AgentStateDelta` to GraphDB and Weaviate. |
| `/ingest_agent_state` | POST | Persist an `AgentState` to GraphDB and Weaviate. |
| `/ingest_agent_request` | POST | Persist an `AgentRequest` to GraphDB and Weaviate. |
| `/ingest_edge` | POST | Persist an `Edge` between two artifacts. |
| `/ingest_agent_request` | POST | Persist an `AgentRequest`.
| `/search` | GET | Query the knowledge graph. |
| `/health` | GET | Health‑check.

## Core components

* **GraphDB client** – `clients/graphdb_client.py` provides `post_turtle` to POST Turtle statements.
* **Weaviate client** – `clients/weaviate.py` creates a client and ensures collections exist.
* **Projections** – `projections/graphdb/turtle.py` contains helper functions for converting artifacts to Turtle.
* **Utilities** – `util/` contains helpers for sorting, chunking, and embedding.

## Example usage

```bash
curl -X POST http://localhost:8000/ingest_episode \
  -H 'Content-Type: application/json' \
  -d '{"episode_id": "ep-001", "claims": [...], "evidence": [...]}'
```

---

For a full contract reference, see the `contracts/inference_contracts` package.
