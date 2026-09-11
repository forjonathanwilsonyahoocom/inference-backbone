# FastAPI app for document ingestion and SPARQL proxy
#
# FastAPI container can ingest a single markdown document via HTTP

from fastapi import FastAPI, Query, Request
import httpx
import os
import json
import yaml
import hashlib
import requests
from typing import Optional, Tuple, List, Dict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/inference-backbone")
ONTOLOGY_PREFIX = os.getenv("ONTOLOGY_PREFIX", "http://mindbodyengineer.com/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.42.0.192:11434")
GEN_MODEL = os.getenv("GEN_MODEL", "gpt-oss:20b")

app = FastAPI()

# Include routers for memory ingestion and search
from inference_backbone.fastapi.memory_ingest import router as memory_ingest_router
from inference_backbone.fastapi.memory_search import router as memory_search_router

app.include_router(memory_ingest_router)
app.include_router(memory_search_router)

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def sha1(txt: str) -> str:
    """Return the SHA‑1 hex digest of *txt*.
    """
    return hashlib.sha1(txt.encode("utf-8")).hexdigest()

def log(msg: str, level: str = 'INFO') -> None:
    print(f"[{level}] {msg}")

# ---------------------------------------------------------------------------
# # — parse_markdown
# ---------------------------------------------------------------------------

def parse_markdown(md_text: str) -> Tuple[Optional[Dict], List[str], str]:
    """Parse a markdown string.

    Returns a tuple ``(meta, sections, raw_content)`` where ``meta`` is a
    dictionary of YAML front‑matter (or ``None`` if missing/invalid),
    ``sections`` is a list of section titles (lines starting with ``## ``),
    and ``raw_content`` is the original markdown.
    """
    try:
        parts = md_text.split("---", 2)
    except Exception as exc:
        # Should never happen, but guard against malformed input
        return None, [], md_text

    if len(parts) < 3 or parts[0].strip() != "":
        # No YAML front‑matter block
        return None, [], md_text

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception as exc:
        return None, [], md_text

    if not isinstance(meta, dict):
        return None, [], md_text

    body = parts[2]
    sections = [s.strip() for s in body.split("\n") if s.startswith("## ")]
    return meta, sections, md_text

# ---------------------------------------------------------------------------
# — extract_metadata_from_llm
# ---------------------------------------------------------------------------

def ask(query: str) -> str:
    """Send *query* to the Ollama endpoint and return the raw response.
    """
    json_prompt = {
        "model": GEN_MODEL,
        "prompt": query,
        "stream": False,
        "system": "",
    }
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=json_prompt, timeout=1000)
    r.raise_for_status()
    resp = r.json()
    raw = resp.get("response", "")
    if not raw and resp.get("thinking"):
        raw = resp["thinking"]
    return raw.strip()


def extract_metadata_from_llm(md_content: str) -> Optional[Dict]:
    """Ask Ollama to parse the document and return a metadata dict.

    Returns ``None`` if the LLM could not produce a valid JSON object.
    """
    prompt = f"""
You are a semantic‑web assistant.  Given the following Markdown document, extract the metadata fields shown below and return **exactly** a JSON object that contains *all* of them – even if the value is empty.

**Required keys (always present, never `null`):**
- `title`        – string, the first `##` line (or empty if missing)
- `category`     – string from the `category:` line in the YAML header, or empty
- `status`       – string from the `status:` line (default "Draft" if missing)
- `keywords`     – array of strings from the `keywords:` list; empty array if missing
- `related`      – array of strings (the keys from the `related:` mapping); empty array if missing

**Important:**
- Do **not** add any other keys.
- Do **not** wrap the JSON in code fences or add explanatory text.
- If you find an alternate meta system in the content, infer the mapping to the requested keys from the values you discover.
- If a value cannot be inferred, use an empty string for a string field or an empty array for a list field.
- The JSON must be **valid** (no trailing commas, no comments).

Here is the document:

{md_content}

Respond with the JSON only.
"""
    try:
        return json.loads(ask(prompt))
    except Exception as exc:
        print(f"[WARN] LLM extraction failed: {exc}")
        return None

# ---------------------------------------------------------------------------
#  — build_turtle
# ---------------------------------------------------------------------------
from rdflib import Graph, Namespace, Literal, URIRef, RDF
from rdflib.namespace import XSD


def build_turtle(meta: Dict, sections: List[str], doc_id: str, body: str = "") -> str:
    """Build a Turtle document from metadata and sections.

    Uses the ``ONTOLOGY_PREFIX`` environment variable as the base IRI.
    """
    g = Graph()
    g.bind("ex", Namespace(ONTOLOGY_PREFIX))
    g.bind("rdf", RDF)
    g.bind("rdfs", Namespace("http://www.w3.org/2000/01/rdf-schema#"))
    g.bind("owl", Namespace("http://www.w3.org/2002/07/owl#"))
    g.bind("xsd", Namespace("http://www.w3.org/2001/XMLSchema#"))

    doc_uri = URIRef(f"{ONTOLOGY_PREFIX}Document{doc_id}")
    g.add((doc_uri, RDF.type, Namespace(ONTOLOGY_PREFIX).Document))

    g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasTitle, Literal(meta.get("title", ""))))
    g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasCategory, Literal(meta.get("category", ""))))
    g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasStatus, Literal(meta.get("status", "Draft"))))
    g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasContent, Literal(body, datatype=XSD.string)))

    for kw in meta.get("keywords", []):
        g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasKeyword, Literal(kw)))

    for sec in sections:
        sec_hash = sha1(sec)
        sec_uri = URIRef(f"{ONTOLOGY_PREFIX}Section_{doc_id}_{sec_hash}")
        g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasSection, sec_uri))

    for rel in meta.get("related", []):
        rel_uri = URIRef(f"{ONTOLOGY_PREFIX}Document{rel}")
        g.add((doc_uri, Namespace(ONTOLOGY_PREFIX).hasRelatedArtifact, rel_uri))

    return g.serialize(format="turtle")

# ---------------------------------------------------------------------------
# — post_to_graphdb
# ---------------------------------------------------------------------------

def post_to_graphdb(turtle: str) -> Tuple[int, str]:
    """POST *turtle* to GraphDB and return (status_code, response_text)."""
    url = f"{GRAPHDB_URL}/statements"
    headers = {
        "Content-Type": "application/x-turtle",
        "Accept": "application/sparql-results+json",
    }
    try:
        r = requests.post(url, data=turtle.encode("utf-8"), headers=headers, timeout=30)
        r.raise_for_status()
        log(f"✅ POSTed {url}")
        return r.status_code, r.text
    except requests.HTTPError as exc:
        log(f"❌ POST failed for {path}: {exc.response.status_code} {exc.response.text}", level='ERROR')
        return exc.response.status_code, exc.response.text
    except requests.RequestException as exc:
        log(f"❌ Network error for {path}: {exc}", level='ERROR')
        return 0, str(exc)

# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------
@app.post("/ingest")
async def ingest(request: Request):
    """Ingest a single markdown document.

    Request body must be JSON with keys:
    - ``content``: raw markdown string
    - ``doc_id`` (optional): override the automatically derived SHA‑1
    """
    try:
        body = await request.json()
    except Exception as exc:
        return {"status": "error", "detail": f"Invalid JSON: {exc}"}

    content = body.get("content")
    if not content:
        return {"status": "error", "detail": "Missing 'content' field"}

    doc_id = body.get("doc_id") or sha1(content)

    # 1. Parse markdown
    meta, sections, raw_content = parse_markdown(content)
    llm_fallback = False
    if meta is None:
        # 2. Fallback to LLM extraction
        meta = extract_metadata_from_llm(content)
        llm_fallback = True
        if meta is None:
            return {
                "status": "error",
                "doc_id": doc_id,
                "detail": "Metadata extraction failed (no front‑matter and LLM fallback failed)",
            }

    # 3. Validate mandatory title
    if not meta.get("title"):
        return {
            "status": "error",
            "doc_id": doc_id,
            "detail": "Missing required title in metadata",
        }

    # 4. Build Turtle
    try:
        turtle = build_turtle(meta, sections, doc_id, body=raw_content)
    except Exception as exc:
        return {
            "status": "error",
            "doc_id": doc_id,
            "detail": f"Turtle generation failed: {exc}",
        }

    # 5. POST to GraphDB
    graphdb_status, graphdb_detail = post_to_graphdb(turtle)
    if graphdb_status >= 400:
        return {
            "status": "error",
            "doc_id": doc_id,
            "graphdb_status": graphdb_status,
            "detail": f"GraphDB error: {graphdb_detail}",
        }

    return {
        "status": "ok",
        "doc_id": doc_id,
        "graphdb_status": graphdb_status,
        "detail": "Ingested successfully",
        "llm_fallback": llm_fallback,
    }

@app.get("/sparql")
async def sparql(query: str = Query(..., description="SPARQL query")):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            GRAPHDB_URL,
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"},
        )
    r.raise_for_status()
    return r.json()

@app.get("/health")
async def health():
    return {"status": "ok"}
