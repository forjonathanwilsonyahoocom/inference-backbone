"""
routers/ingest_edge.py

Endpoint to ingest a ClaimEvidenceEdge: persist to file, write to GraphDB.
"""
from fastapi import APIRouter, status
from contracts.inference_contracts.claim_evidence_edge import ClaimEvidenceEdge
from projections.graphdb.claim_evidence_edge import write_claim_evidence_edge_to_graphdb
from util.file_persistence import write_to_file
from typing import Dict

ingest_edge_router = APIRouter()

@ingest_edge_router.post("/ingest/claim_evidence_edge", status_code=status.HTTP_201_CREATED)
async def claim_evidence_edge_ingest(payload: ClaimEvidenceEdge) -> Dict:
    """Ingest a ClaimEvidenceEdge.

    1️⃣ Persist the edge to disk.
    2️⃣ Write the ClaimEvidenceEdge to GraphDB.
    3️⃣ Return the edge identifiers.
    """
    try:
        # Persist to file
        identifier = f"{payload.evidence_id}_{payload.claim_id}"
        file_path = write_to_file(
            content=payload,
            location="claim_evidence_edge",
            identifier=identifier,
        )
        print(f"[ingest] Persisted edge to {file_path}")

        # Write to GraphDB
        await write_claim_evidence_edge_to_graphdb(payload)

        return {
            "evidence_id": payload.evidence_id,
            "claim_id": payload.claim_id,
            "identifier" : identifier,
        }
    except Exception as e:
        print("edge_ingest FAILURE", e)
        raise
