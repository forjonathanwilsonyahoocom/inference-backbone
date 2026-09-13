from fastapi import APIRouter
from contracts.inference_contracts.evidence import Evidence
from contracts.inference_contracts.evidence_chunk import EvidenceChunk
from projections.graphdb import write_evidence_to_graphdb
from util.chunker import chunk_text
from typing import List, Dict
from util.embedding_provider import OllamaEmbeddingProvider
from util.identity import context_based_id
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection

ingest_router = APIRouter()

@ingest_router.post("/ingest/evidence")
async def evidence_ingest(payload: Evidence) -> Dict:


    await write_evidence_to_graphdb(payload)
    
    ensure_weaviate_collection("EvidenceChunk")
    
    weaviate_client = get_weaviate_client()
    
    try:
        evidence_chunk_collection = weaviate_client.collections.use("EvidenceChunk")
        embedding_provider = OllamaEmbeddingProvider()
        payload.content_hash = context_based_id(payload.content)

        # 1. Chunk the content
        raw_chunks = chunk_text(payload.content)
        
        chunk_ids = []
        for idx, raw_chunk in enumerate(raw_chunks):
           typed_chunk = EvidenceChunk(
                    chunk_id=context_based_id(raw_chunk),
                    evidence_id=payload.evidence_id,
                    content=raw_chunk,
                    chunk_index=idx,
                    chunk_count=len(raw_chunks),
                    embedding_task="document",
                )
           embedding = await embedding_provider.embed(raw_chunk)
           
           chunk_ids.append(evidence_chunk_collection.data.insert(properties = typed_chunk.model_dump(), vector=embedding))
            
        return {"parent_id": payload.content_hash,
                "chunk_count": len(raw_chunks),
                "chunks": chunk_ids}
    except Exception as e:
        print("evidence_ingest FAILURE" , e)
    finally:
        weaviate_client.close()
    

