"""
routers/ingest_edge.py

Endpoint to ingest a ClaimEvidenceEdge: persist to file, embed, store in Weaviate, write to GraphDB.
"""
from fastapi import APIRouter, status
from contracts.inference_contracts.claim_evidence_edge import ClaimEvidenceEdge
from projections.graphdb.claim_evidence_edge import write_claim_evidence_edge_to_graphdb
from util.file_persistence import write_to_file
from util.identity import context_based_id
from util.embedding_provider import OllamaEmbeddingProvider
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection
from typing import Dict

ingest_edge_router = APIRouter()

@ingest_edge_router.post("/ingest/edge", status_code=status.HTTP_201_CREATED)
async def edge_ingest(payload: ClaimEvidenceEdge) -> Dict:
    """Ingest a ClaimEvidenceEdge.

    1️⃣ Persist the edge to disk.
    2️⃣ Write the ClaimEvidenceEdge to GraphDB.
    3️⃣ Ensure the Weaviate collection "ClaimEvidenceEdge" exists.
    4️⃣ Embed the edge (simple string representation) and store in Weaviate.
    5️⃣ Return the edge identifiers and the Weaviate object id.
    """
    weaviate_client = get_weaviate_client()
    try:
        # Persist to file
        identifier = context_based_id(f"{payload.evidence_id}_{payload.claim_id}")
        file_path = write_to_file(
            content=payload,
            location="edge",
            identifier=identifier,
        )
        print(f"[ingest] Persisted edge to {file_path}")

        # Write to GraphDB
        await write_claim_evidence_edge_to_graphdb(payload)

        # Ensure Weaviate collection
        ensure_weaviate_collection("ClaimEvidenceEdge")
        edge_collection = weaviate_client.collections.use("ClaimEvidenceEdge")

        # Embed a simple representation of the edge
        async with OllamaEmbeddingProvider() as embedding_provider:
            embed_text = f"{payload.evidence_id} {payload.claim_id} {payload.support}"
            embedding = await embedding_provider.embed(embed_text)
            payload.embedding_model = embedding_provider.model

        weaviate_obj = edge_collection.data.insert(
            properties=payload.model_dump(),
            vector=embedding,
        )

        return {
            "evidence_id": payload.evidence_id,
            "claim_id": payload.claim_id,
            "weaviate_id": weaviate_obj,
        }
    except Exception as e:
        print("edge_ingest FAILURE", e)
        raise
    finally:
        weaviate_client.close()
