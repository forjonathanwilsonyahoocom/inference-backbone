# AGENTS.md

This document provides a high‑level overview of the three core agents in the **Inference Backbone** system:

1. **Worker Agent** – Executes LLM runs and orchestrates tool calls.
2. **Validator Agent** – Extracts claims, validates them against evidence, and builds episodes.
3. **Backbone API** – Persists inference artifacts to GraphDB and Weaviate.

## Architecture diagram

```
+----------------+      +----------------+      +----------------+
| Worker Agent   | ---> | Validator Agent| ---> | Backbone API   |
+----------------+      +----------------+      +----------------+
        |                        |                    |
        |                        |                    |
        +----> Docker Broker <----+                    |
```

## Key concepts

* **AgentRequest** – Payload for the worker agent that specifies model, temperature, and mode.
* **Episode** – A structured representation of an entire reasoning trace.
* **Claim** – A discrete, checkable statement extracted from an agent’s final answer.
* **Evidence** – Any artifact (e.g., a file, a web search result) that can support or refute a claim.

## How to run the system

1. **Start the Docker broker** – `docker compose up -d broker`.
2. **Start the worker agent** – `docker compose up -d worker`.
3. **Start the validator agent** – `docker compose up -d validator`.
4. **Start the backbone API** – `docker compose up -d api`.

All services expose a `/health` endpoint for liveness checks.

---

For detailed API contracts, see the `contracts/` package.
