# inference-backbone

## this is under dev currently
today while it does provide agent loop and tools, it only ingests to weaviate and graph db, it does not yet use that info

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
