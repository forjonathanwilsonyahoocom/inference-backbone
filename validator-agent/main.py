import json
import os
import requests

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.42.0.192:11434")
GEN_MODEL = os.getenv("GEN_MODEL", "gpt-oss:20b")

print(f"Using {GEN_MODEL} at {OLLAMA_URL}/")
llm = ChatOllama(base_url=OLLAMA_URL, model=GEN_MODEL, temperature=0.01)

CLAIM_EXTRACTION_PROMPT = """You are part of a multi stage claim-checking validator. You will be given:
1. A TASK that an AI agent was asked to perform.
2. The agent's FINAL RESPONSE — what it reported back to the user.

Your job: extract each discrete, checkable factual claim from the FINAL
RESPONSE, and give it an importance value from 0 to 1, where 1 indicates a very important claim and 0 means this claim has only marginal value

Output format:
- A list of claims, each with a unique claim_id (e.g., "claim_1") and the
  claim text.

Respond with ONLY a JSON object, no other text, no markdown fences, in this
exact shape:
{
  "claims": [
    {"claim_id": "claim_1", "text": "<claim as stated>", "importance" : <numeric importance assigned>},
    {"claim_id": "claim_2", "text": "<claim as stated>", "importance" : <numeric importance assigned>}
  ]
}
"""

VALIDATION_PROMPT = """You are part of a multi stage claim-checking validator. You will be given:
1. JSON formatted list of claims
3. An EVIDENCE_ITEM — an actual tool call the agent made and their real results.

IMPORTANT: The EVIDENCE_ITEM is part of the authoritative record.

Your job: for each claim rate from 0 to 1 whether that claim is directly supported by the EVIDENCE_ITEM, 
1 means this claim is well supported by this EVIDENCE_ITEM, 
0 means this EVIDENCE_ITEM is not related to this claim

Rules:
- A claim is "supported" only if the EVIDENCE_ITEM contains a tool result that
  actually backs it up. Do not use your own outside knowledge to decide a
  claim is true — you are checking traceability to evidence, not correctness
  in the abstract.
- A claim the agent asserted that this EVIDENCE_ITEM does not support should result in a 0 rating for this EVIDENCE_ITEM
  even if it sounds plausible.
- it is completely possible that an EVIDENCE_ITEM does not support any of the listed claims
- it is equally possible that an EVIDENCE_ITEM supports multiple claims at various degrees

Respond with ONLY a JSON object, no other text, no markdown fences, in this
exact shape:
{ "support_map": {
    "claim_1": {"supported": <numeric assigned support>},
    "claim_3": {"supported": <numeric assigned support>},
    "claim_2": {"supported": <numeric assigned support>}
}}
"""

class ClaimsRequest(BaseModel):
    task_description: str
    final_response: str
    execution_id: str

class ValidateRequest(BaseModel):
    claims_map: str
    execution_id: str

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


def build_evidence_text(e: dict]) -> str:
    try:
        iteration = int(e.get('event_id').split('-')[-1])
        tool = e.get('evidence_type', 'Nothing') #this will be the name of the tool called
        result = str(e.get('content', 'None' )) #this is the result of the tool call
        metadata = str(e.get('metadata')) #includes args to tool
        return f"- iteration {iteration}: called `{tool}` with metadata {metadata} -> result: {result}"
    except Exception as exc:
        print(exc)
        print(e)
        return None

def parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"): text.rfind("}") + 1]
    return json.loads(text)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/extract_claims")
def extract_claims(req: ClaimsRequest):
    user_content = f"TASK:\n{req.task_description}\n\nFINAL RESPONSE:\n{req.final_response}"
    messages = [SystemMessage(content=CLAIM_EXTRACTION_PROMPT), HumanMessage(content=user_content)]
    result = None
    last_error = None
    for _ in range(3):
        try:
            response = llm.invoke(messages)
            result = parse_json_response(response.content)
            break
        except Exception as exc:
            last_error = str(exc)
    if result is None:
        return {"error": f"Claim extaction failed after retries: {last_error}"}
    return result
    
@app.post("/validate")
def validate(req: ValidateRequest):
    try:
        events = fetch_evidence_events(req.execution_id)
    except Exception as exc:
        return {"error": f"Failed to fetch evidence: {exc}"}
    validation_results = []
    for e in events:
        evidence_text = build_evidence_text(e)
        user_content = f"CLAIMS:\n{req.claims_map}\n\nEVIDENCE_ITEM:\n{evidence_text}"
        messages = [SystemMessage(content=VALIDATION_PROMPT), HumanMessage(content=user_content)]
        result = None
        last_error = None
        for _ in range(3):
            try:
                response = llm.invoke(messages)
                result = parse_json_response(response.content)
                break
            except Exception as exc:
                last_error = str(exc)
        if result is None:
            result = {"error": f"Validation failed after retries: {last_error}"}
        validation_results.append({"event_id" : e["event_id"], "result" : result})
    return {"support" : validation_results}
