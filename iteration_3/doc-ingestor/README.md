# README.md for doc-ingestor
# Markdown ↔ GraphDB Ingestion Service

This container provides a lightweight, manual‑trigger ingestion pipeline that
clones a Markdown repository, parses each file for metadata and section
titles, serialises the data as Turtle, and POSTs it to a GraphDB
repository.

## Usage

```bash
docker compose up doc-ingestor
```

The container will:

1. Clone the repository specified by `REPO_URL` into `CLONE_DIR`.
2. Walk all `*.md` files.
3. Build a Turtle fragment for each file.
4. POST the fragment to `GRAPHDB_URL`.
5. Log progress to stdout.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REPO_URL` | `git@github.com:forjonathanwilsonyahoocom/cae.git` | SSH URL of the docs repo. |
| `CLONE_DIR` | `/data/docs` | Where the repo is cloned inside the container. |
| `GRAPHDB_URL` | `http://graphdb:7200/repositories/inference-backbone` | Endpoint to POST Turtle statements. |
| `ONTOLOGY_PREFIX` | `http://example.org/` | Base namespace for the `ex:` prefix. |

### Example Docker‑Compose snippet

```yaml
services:
  doc-ingestor:
    build: ./doc_ingest
    environment:
      REPO_URL: "git@github.com:forjonathanwilsonyahoocom/cae.git"
      CLONE_DIR: "/data/docs"
      GRAPHDB_URL: "http://graphdb:7200/repositories/inference-backbone"
      ONTOLOGY_PREFIX: "http://example.org/"
    volumes:
      - ./cae:/data/docs:ro   # optional, if you want to keep the repo locally
```
