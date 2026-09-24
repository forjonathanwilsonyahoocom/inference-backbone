"""
routers/ingest_claim.py

Endpoint to ingest a Claim: persist to file, embed, store in Weaviate, write to GraphDB.
"""
from fastapi import APIRouter
from contracts.inference_contracts.claim import Claim
from projections.graphdb.claim import write_claim_to_graphdb
from util.file_persistence import write_to_file
from util.identity import context_based_id
from util.embedding_provider import OllamaEmbeddingProvider
from clients.weaviate import get_weaviate_client, ensure_weaviate_collection
from typing import Dict

ingest_claim_router = APIRouter()

@ingest_claim_router.post("/ingest/claim")
async def claim_ingest(payload: Claim) -> Dict:
    """Ingest a Claim.

    1️⃣ Persist the Claim to disk.
    2️⃣ Ensure the Weaviate collection "Claim" exists.
    3️⃣ Embed the claim content.
    4️⃣ Store the Claim in Weaviate with the embedding vector.
    5️⃣ Write the Claim to GraphDB.
    6️⃣ Return the claim_id and the Weaviate object id.
    """
    weaviate_client = get_weaviate_client()
    try:
        # claim_id is required by Pydantic; it should be supplied by the caller
        # Persist to file
        file_path = write_to_file(
            content=payload,
            location="claim",
            identifier=str(f"{payload.execution_id}-{payload.claim_number}",
        )
        print(f"[ingest] Persisted claim to {file_path}")

        # Write to GraphDB
        await write_claim_to_graphdb(payload)

        # Ensure Weaviate collection
        ensure_weaviate_collection("Claim")
        claim_collection = weaviate_client.collections.use("Claim")

        # Embed content
        async with OllamaEmbeddingProvider() as embedding_provider:
            embedding = await embedding_provider.embed(payload.content)

        # Insert into Weaviate
        weaviate_obj = claim_collection.data.insert(
            properties=payload.model_dump(),
            vector=embedding,
        )

        return {
            "claim_id": payload.claim_id,
            "weaviate_id": weaviate_obj,
        }
    except Exception as e:
        print("claim_ingest FAILURE", e)
        raise
    finally:
        weaviate_client.close()
