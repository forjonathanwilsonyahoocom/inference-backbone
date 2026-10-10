"""
routers/ingest_agent_state.py
"""
from fastapi import APIRouter
from contracts.inference_contracts.agent_state import AgentState
from contracts.inference_contracts.info_chunk import InfoChunk
from util.chunker import chunk_text
from typing import List, Dict
from util.embedding_provider import OllamaEmbeddingProvider
from util.file_persistence import write_to_file
from util.identity import context_based_id
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection
from routers.retrieval import load_document

ingest_agent_state_router = APIRouter()


@ingest_agent_state_router.post("/ingest/agent_state")
async def agent_state_ingest(payload: AgentState) -> Dict:
    """
    /ingest/agent_state endpoint takes the distillation object from the distillation agent
    and chunks into weaviate and saves the state object
    """

    weaviate_client = get_weaviate_client()
    
    try:

        payload.content_hash = context_based_id(payload.model_dump_json(indent=2))
                        
        file_path = write_to_file(
                        content=payload,
                        location="agent_state",
                        identifier=payload.state_id,
                    )
                    
        print(f"[ingest] Persisted AgentState to {file_path}")

        ensure_weaviate_collection("InfoChunk")
        
        info_chunk_collection = weaviate_client.collections.use("InfoChunk")

        # ---- 1️⃣  Embed with a context‑manager ----
        async with OllamaEmbeddingProvider() as embedding_provider:
            total_chunk_count = 0
            chunk_ids = []
            for section in ["artifacts", "claims", "understandings", "hypotheses", "completed_steps"]:
                for i, section_item in enumerate(getattr(payload, section, [])):
                    section_item_text = ""
                    for field in section_item:
                        section_item_text += str(getattr(section_item, field, ""))
                                
                    raw_chunks = chunk_text(section_item_text)
                    total_chunk_count += len(raw_chunks)
                    for idx, raw_chunk in enumerate(raw_chunks):
                        typed_chunk = InfoChunk(
                            chunk_id=context_based_id(raw_chunk),
                            execution_id=payload.execution_id,
                            source_id=payload.state_id,
                            info_type=F"AgentState.{section}"
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
            "chunk_count": total_chunk_count,
            "chunks": chunk_ids,
            "file_path" : file_path,
        }

    except Exception as e:
        print("ingest_agent_state FAILURE", e)
        raise
    finally:
        # ---- 2️⃣  Close the Weaviate client ----
        weaviate_client.close()


