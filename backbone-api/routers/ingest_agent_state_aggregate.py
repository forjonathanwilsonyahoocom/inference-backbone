"""
routers/ingest_agent_state.py
"""
from fastapi import APIRouter
from contracts.inference_contracts.agent_state import AgentState
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

ingest_agent_state_aggregate_router = APIRouter()

@ingest_agent_state_aggregate_router.post("/ingest/agent_state_aggregate")
async def agent_state_ingest(payload: InfoContainer[Dict]) -> Dict:
    """
    /ingest/agent_state_aggregate endpoint takes the aggregated distillation object after delta is applied
    and saves the state object
    """
    
    try:
        print("ingesting agent state aggregate", validate_artifact_id(payload.info.id))
        
        payload.info.content_hash = context_based_id(payload.model_dump_json(indent=2))
                        
        file_path = write_to_file(
                        content=payload,
                        location="agent_state_aggregate",
                        identifier=payload.info.id,
                    )
                    
        print(f"[ingest] Persisted agent_state_aggregate to {file_path}")

        return {
            "content_hash": payload.info.content_hash,
            "file_path" : file_path,
        }

    except Exception as e:
        print("ingest_agent_state_aggregate FAILURE", e)
        raise

