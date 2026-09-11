# Evidence Contract v1

This directory contains the JSON Schema contract for the `EvidenceChunk` data structure used to track evidence from the inference backbone.

## Files

- **schema.json** - JSON Schema definition for the `EvidenceChunk` object
- **example.json** - A valid example instance conforming to the schema
- **README.md** - This file

## Schema Overview

The `EvidenceChunk` schema captures:

- **content** - The text content of the evidence chunk
- **evidence_id** - Unique identifier for this evidence piece
- **execution_id** - Identifier for the execution/context that produced this evidence
- **event_id** - Identifier for the event that triggered this evidence
- **source_type** - Type of source (e.g., "reasoner", "llm", "file")
- **source_name** - Name of the specific source
- **source_url** - URL of the source (if applicable)
- **content_hash** - Hash of the content for deduplication
- **chunk_index** - Index within a chunked document
- **chunk_count** - Total number of chunks
- **embedding_model** - Model used for embedding
- **embedding_task** - Task type for the embedding

## Usage

This schema is used to validate evidence data before ingestion into the knowledge graph and vector store.
