"""
routers/ingest_final_answer.py
"""
from fastapi import APIRouter
from contracts.inference_contracts.final_answer import FinalAnswer
from contracts.inference_contracts.info_chunk import InfoChunk
from util.chunker import chunk_text
from typing import List, Dict
from util.embedding_provider import OllamaEmbeddingProvider
from util.file_persistence import write_to_file
from util.identity import context_based_id
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection

ingest_final_answer_router = APIRouter()


@ingest_final_answer_router.post("/ingest/final_answer")
async def ingest_final_answer(payload: FinalAnswer) -> Dict:
    """
    /ingest/final_answer endpoint takes final_answer and persists to file after generating content hash
    content is chunked and vector indexed into weaviate to allow immediate recall by agent
    """

    weaviate_client = get_weaviate_client()
    
    try:

        payload.content_hash = context_based_id(payload.content)
                        
        file_path = write_to_file(
                        content=payload,
                        location="final_answer",
                        identifier=payload.final_answer_id,
                    )
                    
        print(f"[ingest] Persisted final_answer {file_path}")

        ensure_weaviate_collection("InfoChunk")
        
        evidence_chunk_collection = weaviate_client.collections.use("InfoChunk")

        # ---- 1️⃣  Embed with a context‑manager ----
        async with OllamaEmbeddingProvider() as embedding_provider:
                        
            raw_chunks = chunk_text(payload.content)
            for idx, raw_chunk in enumerate(raw_chunks):
                typed_chunk = InfoChunk(
                    chunk_id=context_based_id(raw_chunk),
                    execution_id=payload.execution_id,
                    source_id=payload.final_answer_id,
                    info_type="FinalAnswer",
                    instance_number=payload.instance_number,
                    content=raw_chunk,
                    chunk_index=idx,
                    chunk_count=len(raw_chunks),
                )
                # Embed only the center part of the chunk to avoid overlapping context
                # If the chunk is shorter than twice the overlap, embed the whole chunk
                overlap = 200  # same as chunker default
                if len(raw_chunk) > 2 * overlap:
                    center_chunk = raw_chunk[overlap : len(raw_chunk) - overlap]
                else:
                    center_chunk = raw_chunk
                embedding = await embedding_provider.embed(center_chunk)
                typed_chunk.embedding_model = embedding_provider.model
                chunk_ids.append(
                    info_chunk_collection.data.insert(
                        properties=typed_chunk.model_dump(), vector=embedding
                    )
                )

        return {
            "content_hash": payload.content_hash,
            "chunk_count": len(raw_chunks),
            "chunks": chunk_ids,
            "file_path" : file_path,
        }

    except Exception as e:
        print("ingest_final_answer FAILURE", e)
        raise
    finally:
        # ---- 2️⃣  Close the Weaviate client ----
        weaviate_client.close()


