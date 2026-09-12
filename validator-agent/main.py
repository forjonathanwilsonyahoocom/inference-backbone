import json
import os

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.42.0.192:11434")
GEN_MODEL = os.getenv("GEN_MODEL", "gpt-oss:20b")

print(f"Using {GEN_MODEL} at {OLLAMA_URL}/")
llm = ChatOllama(base_url=OLLAMA_URL, model=GEN_MODEL, temperature=0.01)

VALIDATION_PROMPT = """You are a claim-checking validator. You will be given:
1. A TASK that an AI agent was asked to perform.
2. The agent's FINAL RESPONSE — what it reported back to the user.
3. An EVIDENCE LOG — the actual tool calls the agent made and their real results.
4. SUPPLEMENTAL EVIDENCE — artifacts retrieved from semantic evidence (Weaviate).

IMPORTANT: The EVIDENCE LOG is the authoritative record. The SUPPLEMENTAL
EVIDENCE is a candidate pool only — it is NOT automatically trusted.

Your job: extract each discrete, checkable factual claim from the FINAL
RESPONSE, then decide whether that claim is directly supported by something
in the EVIDENCE LOG or SUPPLEMENTAL EVIDENCE.

Rules:
- A claim is "supported" only if the evidence log contains a tool result that
  actually backs it up. Do not use your own outside knowledge to decide a
  claim is true — you are checking traceability to evidence, not correctness
  in the abstract.
- A claim the agent asserted with no matching tool result is "unsupported",
  even if it sounds plausible.
- SUPPLEMENTAL EVIDENCE is a candidate pool. If a retrieved artifact matches
  a claim, it is a candidate — the validator must still determine whether
  it actually supports the claim. Do not blindly trust retrieved evidence.
- Distinguish evidence provenance in your response:
  * "direct" — came from the original execution events
  * "retrieved" — came from semantic evidence search
- Ignore stylistic/summary sentences that make no checkable factual claim
  (e.g. "Both sources agree").
- Ignore claims about the agent's own process (e.g. "I searched the web")
  unless the process claim itself is checkable against the evidence log
  (e.g. "I checked three sources" when only one tool call exists).

Respond with ONLY a JSON object, no other text, no markdown fences, in this
exact shape:
{{
  "claims": [
    {{"text": "<claim as stated>", "supported": true|false, "evidence": "<short reference to the supporting tool result, or null>", "provenance": "direct"|"retrieved"}}
  ],
  "overall_verdict": "supported" | "partially_supported" | "unsupported"
}}
"""


class ValidateRequest(BaseModel):
    task_description: str
    final_response: str
    events: list[dict]
    supplemental_evidence: list[dict] = []


def build_evidence_text(events: list[dict], supplemental_evidence: list[dict] = None) -> str:
    evidence_events = [
        e for e in events if e.get("tool") not in ("response", "error_response")
    ]
    if not evidence_events and not supplemental_evidence:
        return "(no tool calls were made)"

    lines = []
    for e in evidence_events:
        lines.append(
            f"- iteration {e.get('iteration')}: called `{e.get('tool')}` "
            f"with args {e.get('args')} -> result: {str(e.get('result'))[:1000]}"
        )
    if supplemental_evidence:
        lines.append("")
        lines.append("SUPPLEMENTAL EVIDENCE (retrieved from semantic evidence):")
        for ev in supplemental_evidence:
            lines.append(f"  - [retrieved] {ev.get('artifact_id', '?')}")
            lines.append(f"    source: {ev.get('source', '?')}")
            lines.append(f"    execution_id: {ev.get('execution_id', '?')}")
            lines.append(f"    event_id: {ev.get('event_id', '?')}")
            lines.append(f"    -> {ev.get('content', '')}")
    return "\n".join(lines)


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


@app.post("/validate")
def validate(req: ValidateRequest):
    evidence_text = build_evidence_text(req.events, req.supplemental_evidence)

    user_content = (
        f"TASK:\n{req.task_description}\n\n"
        f"FINAL RESPONSE:\n{req.final_response}\n\n"
        f"EVIDENCE LOG:\n{evidence_text}"
    )

    messages = [
        SystemMessage(content=VALIDATION_PROMPT),
        HumanMessage(content=user_content),
    ]

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
        return {"error": f"Validation failed after retries: {last_error}"}

    return result
