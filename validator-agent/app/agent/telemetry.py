import httpx
from datetime import datetime, UTC
from typing import List, Dict
import json
from contracts.inference_contracts.claim import Claim
from contracts.inference_contracts.claim_evidence_edge import ClaimEvidenceEdge

from contracts.general_contracts.text_analysis import ReportForEpisodeExtraction

from contracts.validation_contracts.extraction import ExtractionResult, ExtractionClaim

from contracts.inference_contracts.episode import Episode

async def build_evidence_text(e: dict) -> str:
    try:
        iteration = int(e.get('evidence_id').split('-')[-1])
        tool = e.get('evidence_type', 'Nothing') #this will be the name of the tool called
        result = str(e.get('content', 'None' )) #this is the result of the tool call
        metadata = str(e.get('metadata')) #includes args to tool
        return f"- iteration {iteration}: called `{tool}` with metadata {metadata} -> result: {result}"
    except Exception as exc:
        print(exc)
        print(e)
        return ""
        
async def build_clean_claims_list(claims: List[Claim]) -> list[dict]:
    """
    trim off persistence details only preserving key elements for llm
    """
    return_list = []
    for claim in claims:
        return_list.append({"claim_id" : claim.claim_id,
                            "content" : claim.content,
                            "importance" : claim.importance})
    return return_list

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
                        json=payload.model_dump(mode="json").encode("utf8"),
                    )
                except Exception as e:
                    print(f"[Claim ingestion] failed for edge {payload}: {e}")

# ---------------------------------------------------------------------------
# Helper: send a claim result to the claim ingestion endpoint
# ---------------------------------------------------------------------------

async def ingest_claims(config: dict, execution_id: str, claims_extracted: ExtractionResult) -> List[Claim]:
    now = datetime.now(UTC).isoformat()
    base_url = "http://backbone-api:8000"
    claims_persisted: List[Claim] = []
    async with httpx.AsyncClient(timeout=10) as client:
        for i, extracted_claim in enumerate(claims_extracted.claims):
            claim_id = f"{execution_id}-{i}"
            
            claim_to_persist = Claim(
                claim_id=claim_id,
                instance_number=i,
                importance=float(extracted_claim.importance),
                model_name=config['model'],
                execution_id=execution_id,
                content=extracted_claim.text, 
                observed_at=now,
                retrieved_at=now,
                validator_version="1.0.1",
            )
            claims_persisted.append(claim_to_persist)
            try:
                await client.post(
                    f"{base_url}/ingest/claim",
                    json=claim_to_persist.model_dump(mode="json"),
                )
            except Exception as e:
                print(f"[Claim ingestion] failed for claim {claim_id}: {e}")
    return claims_persisted
    

async def ingest_episode(config: dict, execution_id: str, episode: Episode) :
    now = datetime.now(UTC).isoformat()
    base_url = "http://backbone-api:8000"
    info = InfoNode(id=f"{execution_id}-1",
                    execution_id=execution_id,
                    model=config["model"],
                    )
    async with httpx.AsyncClient(timeout=10) as client:
        payload = InfoContainer[Episode](info=info,
                                        contains=episode)
        try:
            await client.post(
                f"{base_url}/ingest/episode",
                json=payload.model_dump(mode="json").encode("utf8"),
            )
        except Exception as e:
            print(f"[Episode ingestion] failed for episode {episode}: {e}")
            raise
    

    
async def fetch_events(object_type: str, execution_id: str) -> List[Dict]:
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. List evidence IDs
        list_resp = await client.get(f"{base_url}/list/{object_type}/{execution_id}")
        if list_resp.status_code != 200:
            raise RuntimeError(f"Failed to list {object_type} for {execution_id}: {list_resp.text}")
        list_data = list_resp.json()
        
        # Handle both list of IDs and dict with 'evidence_ids' key
        if isinstance(list_data, dict) and "evidence_ids" in list_data:
            evidence_ids = list_data["evidence_ids"]
        else:
            raise ValueError(f"Unexpected response format for {object_type} list: {list_data}")

        # 2. Fetch file content for each ID
        events = []
        for eid in evidence_ids:
            file_resp = await client.get(f"{base_url}/file/{object_type}/{eid}")
            if file_resp.status_code != 200:
                continue
            try:
                events.append(file_resp.json())
            except Exception:
                continue
        return events


async def fetch_closest_evidence(to_claims: list[Claim], execution_id: str) -> List[Dict]:
    base_url = "http://backbone-api:8000"
    nearby = set()
    async with httpx.AsyncClient(timeout=10) as client:
       
        # 2. search for nearby evidence to claim content
        for claim in to_claims:
            payload = {
              "query": claim.content,
              "limit" : 20,
              "execution_id" : execution_id,
            }
            #print(payload)
            file_resp = await client.post(f"{base_url}/search/evidence",
                                          json=json.dumps(payload).encode("utf8"))
            if file_resp.status_code != 200:
                continue
            try:
                search_results = file_resp.json()
                for y in search_results:
                    #build up distinct list of evidence with content close to claim content
                    nearby.add(y["properties"]["evidence_id"])
            except Exception:
                continue
        print(nearby)
        # 2. Fetch file content for each ID in set
        events = []
        for eid in nearby:
            file_resp = await client.get(f"{base_url}/file/evidence/{eid}")
            if file_resp.status_code != 200:
                continue
            try:
                events.append(file_resp.json())
            except Exception:
                continue
        print(f"recovered {len(events)} evidence docs")
        return events


async def get_full_trace_file_names(execution_id: str) -> List[Dict]:
    base_url = "http://backbone-api:8000"
    async with httpx.AsyncClient(timeout=10) as client:
        # 1. List evidence IDs
        trace_resp = await client.get(f"{base_url}/full_trace/{execution_id}")
        if trace_resp.status_code != 200:
            raise RuntimeError(f"Failed to get_full_trace_file_names for {execution_id}: {trace_resp.text}")
        trace_data = trace_resp.json()
        
        files= []
        for k in trace_data["nodes"]:
            for v in  trace_data["nodes"][k]:
                files.append(f"{k}/{v}.json")

        return files


async def assemble_report_from_files(files: list[str]) -> ReportForEpisodeExtraction:
    base_url = "http://text-analysis:8000"
        
    async with httpx.AsyncClient(timeout=100) as client:
        payload = {
          "files": files
        }
        print(payload)
        report_resp = await client.post(f"{base_url}/prep_report",
                                      data=json.dumps(payload).encode("utf8"),
                                      headers={"Content-Type": "application/json"})
        if report_resp.status_code != 200:
            raise Exception("failed to get report from files")
        
        result = ReportForEpisodeExtraction.parse_obj(report_resp.json())
        
        return result
 
