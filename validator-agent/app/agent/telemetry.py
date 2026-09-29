import httpx
from datetime import datetime, UTC
from typing import List, Dict
from contracts.inference_contracts.claim import Claim
from contracts.inference_contracts.claim_evidence_edge import ClaimEvidenceEdge

# ---------------------------------------------------------------------------
# Helper: trigger supporting evidence to be fully ingested
# ---------------------------------------------------------------------------

async def promote_supporting_evidence(identifier: str):
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            await client.get(f"{base_url}/ingest/supporting_evidence/{identifier}")
        except Exception as e:
            print(f"[Supporting evidence ingestion] failed for evidence_id {identifier}: {e}")
            

async def link_claims_to_evidence(config: dict, support_map: dict):
    now = datetime.now(UTC).isoformat()
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        for claim_id, supporting in support_map.items():
            for evidence_id, support in supporting.items():
                payload = ClaimEvidenceEdge(
                    claim_id=claim_id,
                    evidence_id=evidence_id,
                    support=support,
                    model_name=config['model'],
                    observed_at=now,
                    retrieved_at=now,
                )
                try:
                    await client.post(
                        f"{base_url}/ingest/claim_evidence_edge",
                        json=payload.model_dump(mode="json"),
                    )
                except Exception as e:
                    print(f"[Claim ingestion] failed for edge {payload}: {e}")

# ---------------------------------------------------------------------------
# Helper: send a claim result to the claim ingestion endpoint
# ---------------------------------------------------------------------------

async def ingest_claims(config: dict, execution_id: str, claims:  List[Dict]) -> List[Dict]:
    now = datetime.now(UTC).isoformat()
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        for i, claim in enumerate(claims):
            claim_id = f"{execution_id}-{i}"
            claim["claim_id"] = claim_id
            
            payload = Claim(
                claim_id=claim_id,
                claim_number=i,
                importance=float(claim["importance"]),
                model_name=config['model'],
                execution_id=execution_id,
                content=claim["text"], 
                observed_at=now,
                retrieved_at=now,
                validator_version="1.0.1",
            )
            try:
                await client.post(
                    f"{base_url}/ingest/claim",
                    json=payload.model_dump(mode="json"),
                )
            except Exception as e:
                print(f"[Claim ingestion] failed for claim {claim_id}: {e}")
    return claims
    
async def fetch_evidence_events(execution_id: str) -> List[Dict]:
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        list_resp = await client.get(f"{base_url}/list/evidence/{execution_id}")
        if list_resp.status_code != 200:
            raise RuntimeError(f"Failed to list evidence for {execution_id}: {list_resp.text}")
        list_data = list_resp.json()
        evidence_ids = list_data.get("evidence_ids") or (list_data if isinstance(list_data, list) else [])
        events = []
        for eid in evidence_ids:
            file_resp = await client.get(f"{base_url}/file/evidence/{eid}")
            if file_resp.status_code != 200:
                continue
            try:
                events.append(file_resp.json())
            except Exception:
                continue
        return events


