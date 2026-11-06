"""
routers/ingest_agent_state_delta.py
"""
from fastapi import APIRouter
from contracts.inference_contracts.episode import Episode
from contracts.inference_contracts.info import InfoContainer, InfoNode
from contracts.inference_contracts.info_chunk import InfoChunk
from contracts.inference_contracts.validations import validate_artifact_id
from util.chunker import chunk_text
from typing import List, Dict
from util.embedding_provider import OllamaEmbeddingProvider
from util.file_persistence import write_to_file
from util.identity import context_based_id
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection
import uuid
from projections.graphdb.turtle import write_object_to_graphdb

ingest_episode_router = APIRouter()

async def vector_store_episode_part(embedding_provider, info_chunk_collection, chunk_ids, payload: InfoContainer[Episode], section: str, section_id: str, i: int, section_item: str):
    section_item_id = f"{section_id}-{i}"
   
    raw_chunks = chunk_text(section_item)
    for idx, raw_chunk in enumerate(raw_chunks):
        typed_chunk = InfoChunk(
            chunk_id=context_based_id(raw_chunk),
            execution_id=payload.info.execution_id,
            source_id=payload.info.id,
            item_id=section_item_id,
            info_type=F"Episode.{section}",
            instance_number=0,
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
    return chunk_ids
        
@ingest_episode_router.post("/ingest/episode")
async def episode_ingest(payload: InfoContainer[Episode]) -> Dict:
    """
    /ingest/episode endpoint takes the episode object from the episode agent in validator
    and chunks into weaviate and saves the episode object
    """
                               
    weaviate_client = get_weaviate_client()
    
    try:
        print("ingesting episode", validate_artifact_id(payload.info.id))
        
        payload.info.content_hash = context_based_id(payload.model_dump_json(indent=2))
                        
        file_path = write_to_file(
                        content=payload,
                        location="episode",
                        identifier=payload.info.id,
                    )
                    
        print(f"[ingest] Persisted Episode to {file_path}")

        ensure_weaviate_collection("InfoChunk")
        
        info_chunk_collection = weaviate_client.collections.use("InfoChunk")

        mission_string = f"mission: {payload.contains.mission}, outcome: {payload.contains.outcome}"

        # ---- 1️⃣  Embed with a context‑manager ----
        async with OllamaEmbeddingProvider() as embedding_provider:
            chunk_ids = []
            section_id = str(uuid.uuid4())
            chunk_ids = await vector_store_episode_part(embedding_provider, info_chunk_collection, chunk_ids, payload, "mission", section_id, 1, mission_string)

            for section in ["significant_events","findings","lessons","unresolved_questions","evidence_refs"]:
                section_id = str(uuid.uuid4())
                for i, section_item in enumerate(getattr(payload, section, [])):
                    chunk_ids = await vector_store_episode_part(embedding_provider, info_chunk_collection, chunk_ids, payload, section, section_id, i, section_item)
            
        await write_object_to_graphdb(payload, "episode",  payload.info.id)

        return {
            "content_hash": payload.info.content_hash,
            "chunk_count": len(chunk_ids),
            "chunks": chunk_ids,
            "file_path" : file_path,
        }

    except Exception as e:
        print("ingest_agent_state FAILURE", e)
        raise
    finally:
        # ---- 2️⃣  Close the Weaviate client ----
        weaviate_client.close()


