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
        |                         
        |                        
        +----> Docker Broker 
```

## Key concepts

* **AgentRequest** – Payload for the worker agent that specifies model, temperature, and mode.
* **Episode** – A structured representation of an entire reasoning trace.
* **Claim** – A discrete, checkable statement extracted from an agent’s final answer.
* **Evidence** – Any artifact (e.g., a file, a web search result) that can support or refute a claim.

For detailed API contracts, see the `contracts/` package.

## Testing

there is a pattern established in the worker-agent service,
run the ./worker-agent/test.sh to execute tests in the worker-agent service

the script will install the worker-agent so that the paths expressed in the
worker agent service will import correctly
