"""
routers/ingest_agent_request.py

Endpoint to ingest a Claim: persist to file, embed, store in Weaviate, write to GraphDB.
"""
from fastapi import APIRouter
from util.file_persistence import write_to_file
from util.embedding_provider import OllamaEmbeddingProvider
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection
from typing import Dict
from util.identity import context_based_id
import json
from projections.graphdb.turtle import write_object_to_graphdb
from contracts.inference_contracts.worker_agent_request import AgentRequest

ingest_agent_request_router = APIRouter()

def config_identity(scaffold: AgentRequest) -> dict:
    d = scaffold.model_dump()
    d.pop("request")
    d.pop("execution_id")
    return d

@ingest_agent_request_router.post("/ingest/agent_request")
async def agent_request_ingest(payload: AgentRequest) -> Dict:
    """Ingest an agent_request, remove its expected variation fields
    hash to make idempotent name and persist to file.

    """
    try:
      
        persist_version = json.dumps(config_identity(payload), sort_keys=True).encode()
        idempotent_id = context_based_id(persist_version)
        
        file_path = write_to_file(
            content=persist_version,
            location="agent_request",
            identifier=idempotent_id)
        
        print(f"[ingest] Persisted agent_request to {file_path}")

        return {
            "id": idempotent_id
        }
    except Exception as e:
        print("agent_request FAILURE", e)
        raise
