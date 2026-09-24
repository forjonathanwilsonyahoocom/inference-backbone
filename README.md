# inference-backbone

## Overview

`inference-backbone` is a self‑sustaining compute backbone that **powers a human + AI ecosystem**. It orchestrates data ingestion, semantic enrichment, vector similarity, and inference across a distributed knowledge‑graph stack.

### Core Components

- **GraphDB** – stores RDF triples and exposes SPARQL endpoints.
- **Weaviate** – vector store for similarity search.
- **FastAPI** – API gateway exposing ingestion, retrieval, and validation endpoints.
- **Worker Agent** – runs inference loops, collects telemetry, and pushes results to GraphDB/Weaviate.
- **Validator Agent** – verifies claims against the knowledge base.

### Flow

```
Prompt → Worker Agent → (Ingest → GraphDB / Weaviate) → Inference → Validation → API
```

![Agent Dashboard](./readme/agent_dashboard.png)

### Observability

Metrics are exposed via Prometheus and visualised in Grafana. Key metrics include:
- Inference latency
- Query throughput
- GPU utilisation
- Telemetry event counts

---

## Detailed Documentation

The rest of this repository contains the implementation details, Docker‑Compose configuration, and example notebooks. Refer to the `docs/` directory for deeper dives.


for example: collect the output from the worker agent
```python
import requests

url = "http://10.42.0.1:8001/run"

task_description = """

    testing updates to the telemetry, please assert the workspace is empty, then do a web search for OWL reasoning, and write one README.md file that contains the first search result 

"""
payload = {
    "request": task_description,
    "verbose": True,
    "max_iterations":40
}

try:
    response = requests.post(
        url,
        json=payload,  # Serializes the dict and sets Content-Type: application/json
        timeout=1000,
    )

    response.raise_for_status()

    # If the endpoint returns JSON:
    result = response.json()
    print(result["final_response"])

except requests.exceptions.RequestException as error:
    print(f"HTTP request failed: {error}")
```
```bash
✅ **Workspace is empty** – verified.  
✅ **Web search for “OWL reasoning”** – results retrieved.  
✅ **README.md** created with the first search result.

---

### Quick Check
Open `README.md` to confirm the content:

cat README.md

You should see the title, URL, and snippet from the Owlready2 documentation.

---

### Next Steps (Optional)
- **Add more search results**: Append additional entries to the README.  
- **Create a simple script** that fetches the full article content using `web_fetch`.  
- **Set up a local OWL reasoner** (e.g., Owlready2 or Pellet) and link it to a small ontology for experimentation.

Let me know which direction you'd like to explore next!
```

then pass that return val to the validation agent:

```python

url = "http://10.42.0.1:8002/validate"

payload = {
    "task_description": task_description,
    "final_response": result['final_response'] if len(result['final_response'] ) > 5 else "claims to be done",
    "events": result['events']
}
validation_result = {}
try:
    response = requests.post(
        url,
        json=payload,  # Serializes the dict and sets Content-Type: application/json
        timeout=1000,
    )

    response.raise_for_status()

    # If the endpoint returns JSON:
    validation_result = response.json()

except requests.exceptions.RequestException as error:
    print(f"HTTP request failed: {error}")

validation_result

```

```text
{'claims': [{'text': 'Workspace is empty – verified.',
   'supported': True,
   'evidence': 'list_files result',
   'provenance': 'direct'},
  {'text': 'Web search for “OWL reasoning” – results retrieved.',
   'supported': True,
   'evidence': 'web_search result',
   'provenance': 'direct'},
  {'text': 'README.md created with the first search result.',
   'supported': True,
   'evidence': 'write_file result',
   'provenance': 'direct'},
  {'text': 'The README.md contains the title, URL, and snippet from the Owlready2 documentation.',
   'supported': True,
   'evidence': 'write_file result',
   'provenance': 'direct'},
  {'text': "The title in the README.md is 'Reasoning — Owlready2 0.52 documentation - Read the Docs'.",
   'supported': True,
   'evidence': 'write_file result',
   'provenance': 'direct'},
  {'text': "The URL in the README.md is 'https://owlready2.readthedocs.io/en/latest/reasoning.html'.",
   'supported': True,
   'evidence': 'write_file result',
   'provenance': 'direct'},
  {'text': "The snippet in the README.md is 'Before performing reasoning, you need to create all Classes, Properties and Instances, and to ensure that restrictions and disjointnesses / differences have been defined too.'.",
   'supported': True,
   'evidence': 'write_file result',
   'provenance': 'direct'}],
 'overall_verdict': 'supported'}
```
## planned:

An intelligent, autonomous retrieval and ingestion infrastructure designed for agentic workflows. This backbone allows agents to receive a prompt, automatically search the web via headless browser instances, safely parse and chunk document semantics, vector-embed data patterns locally, and traverse information via a distributed GraphQL knowledge layer. 

### 🏗️ System Architecture Flow
```text
                   INFERENCE-BACKBONE
                          │
                 ┌────────┴────────┐
                 │                 │
                 ▼                 ▼
             GraphDB           Weaviate
             "truth"           "similarity"
                 │                 │
                 │                 │
              RDF/SPARQL       vectors/BM25
                 │                 │
                 └────────┬────────┘
                          │
                       FastAPI
                          │
                ┌─────────┴─────────┐
                │                   │
             Worker             Validator
```
