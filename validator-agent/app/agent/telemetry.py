import requests
from typing import Dict, List
from contracts.inference_contracts.claim import Claim
from datetime import datetime, UTC
# ---------------------------------------------------------------------------
# Helper: trigger supporting evidence to be fully ingested
# ---------------------------------------------------------------------------

def promote_supporting_evidence(identifier: str):
    try:
        resp = requests.get(f"http://backbone-api:8000/ingest/supporting_evidence/{identifier}", timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Log but do not raise – evidence is observational
        print(f"[Supporting evidence ingestion] failed for event_id {event_id}: {e}")

# ---------------------------------------------------------------------------
# Helper: send a claim result to the claim ingestion endpoint
# ---------------------------------------------------------------------------

def ingest_claims(execution_id: str, claims:  List[Dict]) -> List[Dict]:
  
    now = datetime.now(UTC).isoformat()
    for i, claim in enumerate(claims):
        claim_id = f"{execution_id}-{i}"
        claim["claim_id"] = claim_id
        try:
            payload = Claim(
                claim_id=claim_id,
                claim_number=i,
                importance=float(claim["importance"]),
                model_name=GEN_MODEL,
                execution_id=execution_id,
                content=claim["text"], 
                observed_at=now,
                retrieved_at=now,
                embedding_task="document", #this seems like a meaningless field
                validator_version="1.0.1",
            )
            resp = requests.post("http://backbone-api:8000/ingest/claim", json=payload.model_dump(mode="json"), timeout=10)
            resp.raise_for_status()
        except Exception as e:
            # Log but do not raise – evidence is observational
            print(f"[Claim ingestion] failed for claim {claim}: {e}")
    return claims



def fetch_evidence_events(execution_id: str) -> list[dict]:
    base_url = "http://backbone-api:8000"
    list_resp = requests.get(f"{base_url}/list/evidence/{execution_id}")
    if list_resp.status_code != 200:
        raise RuntimeError(f"Failed to list evidence for {execution_id}: {list_resp.text}")
    list_data = list_resp.json()
    event_ids = list_data.get("event_ids") or []
    if not event_ids:
        event_ids = list_data if isinstance(list_data, list) else []
    events = []
    for eid in event_ids:
        file_resp = requests.get(f"{base_url}/file/evidence/{eid}")
        if file_resp.status_code != 200:
            continue
        try:
            ev = file_resp.json()
            events.append(ev)
        except Exception:
            continue
    return events


