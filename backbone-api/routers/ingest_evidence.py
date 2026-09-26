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
from routers.retrieval import get_document_file

ingest_evidence_router = APIRouter()


@ingest_evidence_router.post("/ingest/evidence")
async def evidence_file_ingest(payload: Evidence) -> Dict:
"""
/ingest/evidence endpoint takes evidence and persists to file after generating content hash
this evidence has not been validated as supporting 
any claims yet so it does not get indexed into weaviate or graphdb
"""
    try:

        payload.content_hash = context_based_id(payload.content)
                
        file_path = write_to_file(
                        content=payload,
                        location="evidence",
                        identifier=payload.event_id,
                    )
                    
        print(f"[ingest] Persisted evidence to {file_path}")

        return {
            "parent_id": payload.content_hash
        }

    except Exception as e:
        print("evidence_ingest FAILURE", e)
        raise

@ingest_evidence_router.get("/ingest/supporting_evidence/{identifier}")
async def evidence_ingest(identifier: str) -> Dict:
"""
when evidence is found to support a claim we ingest/index into graphdb and weaviate
this keeps our graph as sparse as possible, we can always collect the original 
un-supporting evidence from the files, we collect from the retrieval route func
to assert we are ingesting the original evidence doc 
"""

    weaviate_client = get_weaviate_client()
        
    try:
        document = get_document_file("evidence", identifier)
        payload = Evidence.model_validate_json(document)

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
