"""
routers/ingest_evidence.py
"""
from fastapi import APIRouter
from contracts.inference_contracts.evidence import Evidence
from contracts.inference_contracts.evidence_chunk import EvidenceChunk
from projections.graphdb.evidence import write_evidence_to_graphdb
from util.chunker import chunk_text
from typing import List, Dict
from util.embedding_provider import OllamaEmbeddingProvider
from util.file_persistence import write_to_file
from util.identity import context_based_id
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection

ingest_evidence_router = APIRouter()

@ingest_evidence_router.post("/ingest/evidence")
async def evidence_ingest(payload: Evidence) -> Dict:

    weaviate_client = get_weaviate_client()
        
    try:


        payload.content_hash = context_based_id(payload.content)
                
        file_path = write_to_file(
                        content=payload,
                        location="evidence",
                        identifier=evidence.event_id,
                    )
                    
        print(f"[ingest] Persisted evidence to {file_path}")

        await write_evidence_to_graphdb(payload)

        ensure_weaviate_collection("EvidenceChunk")
        
        evidence_chunk_collection = weaviate_client.collections.use("EvidenceChunk")

        # ---- 1️⃣  Embed with a context‑manager ----
        async with OllamaEmbeddingProvider() as embedding_provider:

            raw_chunks = chunk_text(payload.content)
            chunk_ids = []

            for idx, raw_chunk in enumerate(raw_chunks):
                typed_chunk = EvidenceChunk(
                    chunk_id=context_based_id(raw_chunk),
                    execution_id=payload.execution_id,
                    evidence_id=payload.evidence_id,
                    event_id=payload.event_id,
                    content=raw_chunk,
                    chunk_index=idx,
                    chunk_count=len(raw_chunks),
                    embedding_task="document",
                )
                embedding = await embedding_provider.embed(raw_chunk)

                chunk_ids.append(
                    evidence_chunk_collection.data.insert(
                        properties=typed_chunk.model_dump(), vector=embedding
                    )
                )

        return {
            "parent_id": payload.content_hash,
            "chunk_count": len(raw_chunks),
            "chunks": chunk_ids,
        }

    except Exception as e:
        print("evidence_ingest FAILURE", e)
        raise
    finally:
        # ---- 2️⃣  Close the Weaviate client ----
        weaviate_client.close()
