#!/usr/bin/env python3
"""
GraphDB document ingestor

- Clones the CAE repo (if missing)
- Parses markdown files with YAML front‑matter
- Builds Turtle for each compliant document
- POSTs to GraphDB /repositories/<repo>/statements
"""

import os
import pathlib
import hashlib
import json
import yaml
import requests
import git
from pathlib import Path

from typing import Dict, List, Tuple, Optional

# ---------- configuration ----------
BASE_IRI     = os.getenv('ONTOLOGY_PREFIX', 'http://example.org/')
GRAPHDB_URL  = os.getenv('GRAPHDB_URL', 'http://graphdb:7200/repositories/inference-backbone')
REPO_DIR     = Path(os.getenv('CLONE_DIR', '/data/docs'))
REPO_URL     = os.getenv('REPO_URL', 'git@github.com:forjonathanwilsonyahoocom/cae.git')

# ---------- helpers ----------
def sha1(txt: str) -> str:
    return hashlib.sha1(txt.encode('utf-8')).hexdigest()

def log(msg: str, level: str = 'INFO') -> None:
    print(f"[{level}] {msg}")

# ---------- markdown parser ----------
def parse_markdown(md_path: Path) -> Tuple[Optional[Dict], List[str]]:
    """
    Returns (meta_dict, section_titles) or (None, []) if the file is non‑compliant.
    """
    try:
        txt = md_path.read_text(encoding='utf-8')
    except Exception as exc:
        log(f"⚠️ Cannot read {md_path}: {exc}", level='WARN')
        return None, [], None

    parts = txt.split('---', 2)
    if len(parts) < 3 or not parts[0].strip() == '':
        # no YAML front‑matter block
        return None, [], txt

    try:
        meta = yaml.safe_load(parts[1]) or {}
    except Exception as exc:
        log(f"⚠️ YAML parse error in {md_path}: {exc}", level='WARN')
        return None, [], txt

    if not isinstance(meta, dict):
        log(f"⚠️ YAML not a dict in {md_path}", level='WARN')
        return None, [], txt

    body = parts[2]
    sections = [s.strip() for s in body.split('\n') if s.startswith('## ')]
    return meta, sections, txt

# ---------- Turtle builder ----------
def build_turtle(meta: Dict, sections: List[str], doc_id: str, body="") -> str:
    """
    Return a *complete* Turtle document that starts with prefix declarations.
    """
    # ---- PREFIX BLOCK ----
    prefixes = [
        "@prefix ex:  <http://example.org/> .",
        "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
    ]

    # ---- METADATA TRIPLES ----
    title = meta["title"].replace('"', r'\"')  # escape double quotes
    lines = [
        f"<{BASE_IRI}Document{doc_id}> a ex:Document ;",
        f"  ex:hasTitle \"{meta['title'].replace('\"', r'\\\"')}\" ;",
        f"  ex:hasCategory \"{meta.get('category','').replace('\"', r'\\\"')}\" ;",
        f"  ex:hasStatus  \"{meta.get('status','Draft').replace('\"', r'\\\"')}\" ;",
        f"  ex:hasKeywords \"{', '.join(meta.get('keywords',[]))}\" ;",
        f"  ex:hasRelated  \"{', '.join(meta.get('related',[]))}\" ;",
        f"  ex:hasContent \"{json.dumps(body)[1:-1] }\" ;",
    ]


    for kw in meta.get('keywords', []):
        lines.append(f"  ex:hasKeyword \"{kw}\" ;")

    # ---- SECTION TRIPLES ----
    for sec in sections:
        sec_id = sha1(sec)
        lines.append(f"  ex:hasSection <{BASE_IRI}Section_{sec_id}> ;")

    # ---- RELATED ARTIFACT TRIPLES ----
    for rel in meta.get('related', []):
        lines.append(f"  ex:hasRelatedArtifact <{BASE_IRI}Document{rel}> ;")

    # ---- TERMINATE ----
    lines[-1] = lines[-1].rstrip(" ;") + " ."

    # Combine everything
    return "\n".join(prefixes + [""] + lines)


# ---------- POST to GraphDB ----------
def post_to_graphdb(turtle: str, path: Path) -> None:
    # GraphDB expects Turtle at /repositories/<repo>/statements
    url = f"{GRAPHDB_URL}/statements"
    headers = {
        "Content-Type": "application/x-turtle",
        "Accept": "application/sparql-results+json"
    }

    try:
        r = requests.post(url, data=turtle.encode('utf-8'), headers=headers, timeout=30)
        r.raise_for_status()
        log(f"✅ POSTed {path}")
    except requests.HTTPError as exc:
        log(f"❌ POST failed for {path}: {exc.response.status_code} {exc.response.text}", level='ERROR')
    except requests.RequestException as exc:
        log(f"❌ Network error for {path}: {exc}", level='ERROR')

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://10.42.0.192:11434")


#GEN_MODEL = "qwen3.5:9b"
#GEN_MODEL = "ornith:9b"
GEN_MODEL = "gpt-oss:20b"

last_response = None
SYSTEM_PROMPT = """
The Year is 2026, You are Graph‑Partner, an AI collaborator specialized in building, deploying, and iterating on a semantic‑web/OWL knowledge‑graph stack that runs locally on a Linux server with an NVIDIA RTX 5070 GPU.  

Your primary mission is to help the user (a 48‑year‑old software engineer) create a **self‑sustaining, compute‑backbone** that powers a “human + AI” ecosystem.  You must:

1. **Stay Technical**  
   • Skip any corporate‑HR or job‑search advice.  
   • Focus on concrete tooling, code.

2. **Keep in mind OWL Inference Flow**  
   • think a forward‑chaining reasoner.  
"""

def ask(query):

    json_prompt = {"model": GEN_MODEL, "prompt": query, "stream": False, "system" : SYSTEM_PROMPT}
    # if schema is not None:
    #     json_prompt["format"] = "json"
        
    r = requests.post(f"{OLLAMA_URL}/api/generate",
        json=json_prompt, timeout=1000)
    r.raise_for_status()
    
    resp = r.json()
    raw = resp["response"]
    if (not raw or len(raw) == 0) and resp.get("thinking"):
        raw = resp["thinking"]
    
    return raw.strip()
    
def extract_metadata_from_llm(md_content: str) -> dict | None:
    """Ask Ollama to parse the document and return a dict."""


    prompt = f"""
You are a semantic‑web assistant.  
Given the following Markdown document, extract the metadata fields shown below and return **exactly** a JSON object that contains *all* of them – even 
if the value is empty.

any subset of the required keys is acceptable if some of them are not reachable 

**Required keys (always present, never `null`):**
- `title`        – string, the first `##` line (or empty if missing)
- `category`     – string from the `category:` line in the YAML header, or empty
- `status`       – string from the `status:` line (default `"Draft"` if missing)
- `keywords`     – array of strings from the `keywords:` list; empty array if missing
- `related`      – array of strings (the keys from the `related:` mapping); empty array if missing

**Important:**
- Do **not** add any other keys.
- Do **not** wrap the JSON in code fences or add explanatory text.
- if you find an alternate meta system in the content, infer the mapping to the requested keys from the values you discover
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


# ---------- main ----------

def main() -> None:
    # … clone … (unchanged)
    
    
    for md_path in REPO_DIR.rglob("*.md"):
        meta, sections, raw_content = parse_markdown(md_path)
        
        # If the file lacks a proper front‑matter block
        if meta is None:
            print(f"[INFO] Trying LLM extraction for {md_path}")
            meta = extract_metadata_from_llm(raw_content)
    
            if meta is None:
                log(f"⚠️ Skipping {md_path} – LLM extraction failed", level='WARN')
                continue
            
        # Validate the meta – skip if mandatory title is empty
        if not meta.get("title"):
            print(f"[WARN] Skipping {md_path} – title missing")
            print(meta)
            continue
    
        try:
            doc_id = sha1(md_path.as_posix())
            turtle = build_turtle(meta, sections, doc_id, body=raw_content)
        except Exception as exc:
            log(f"⚠️ Skipping {md_path} – {exc}", level='WARN')
            continue
            
        post_to_graphdb(turtle, md_path)


if __name__ == "__main__":
    main()
