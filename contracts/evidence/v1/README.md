# Evidence Contract v1

This directory contains the JSON Schema contract for the `EvidenceChunk` data structure used to track evidence from the inference backbone.

An Evidence object represents an observation produced or retrieved during an execution. It does not assert that the observed information is true.

## Files

- **schema.json** - JSON Schema definition for the `EvidenceChunk` object
- **example.json** - A valid example instance conforming to the schema
- **README.md** - This file

## Schema Overview

The `EvidenceChunk` schema captures:
- **observed_at** - Time at which the producing tool/system observed or generated the content.
- **retrieved_at** - Time at which the backbone persisted/retrieved the observation.
- **content** - The text content of the evidence chunk
- **evidence_id** - Unique Stable identifier for this particular evidence observation.
- **execution_id** - Identifier for the execution/context that produced this evidence
- **event_id** - Identifier for the event that triggered this evidence
- **source_type** - Type of source (e.g., "reasoner", "llm", "file")
- **source_name** - Name of the specific source
- **source_url** - URL of the source (if applicable)
- **content_hash** - SHA-256 hash of the canonical UTF-8 content representation.
- **chunk_index** - Index within a chunked document
- **chunk_count** - Total number of chunks
- **embedding_model** - Model used for embedding
- **embedding_task** - Task type for the embedding

## Usage

This schema is used to validate evidence data before ingestion into the knowledge graph and vector store.
