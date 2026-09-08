#!/usr/bin/env python3
"""Markdown to Turtle ingestion script.

This script walks the cloned repository, parses each Markdown file for
YAML front‑matter and section titles, builds a Turtle fragment that
represents an ex:Document instance, and POSTs it to the GraphDB
repository.
"""

import hashlib
import os
import pathlib
import sys
import yaml
import requests
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration – read from environment variables
# ---------------------------------------------------------------------------
BASE_IRI = os.getenv("ONTOLOGY_PREFIX", "http://example.org/")
GRAPHDB_URL = os.getenv("GRAPHDB_URL", "http://graphdb:7200/repositories/inference-backbone")
CLONE_DIR = Path(os.getenv("CLONE_DIR", "/data/docs"))

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def sha1(text: str) -> str:
    """Return the SHA‑1 hex digest of *text*.

    Used to generate deterministic IRIs for documents and sections.
    """
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def parse_markdown(md_path: Path):
    """Parse a Markdown file.

    Returns a tuple ``(meta, sections)`` where *meta* is a dict of the
    YAML front‑matter and *sections* is a list of section titles.
    """
    content = md_path.read_text(encoding="utf-8")
    # Split header and body – assume YAML front‑matter delimited by ---
    if not content.startswith("---"):
        raise ValueError(f"{md_path} does not start with YAML front‑matter")
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{md_path} missing closing --- for front‑matter")
    header, body = parts[1], parts[2]
    meta = yaml.safe_load(header) or {}
    # Extract section titles – lines starting with ##
    sections = [line.strip()[3:].strip() for line in body.splitlines() if line.startswith("## ")]
    return meta, sections


def build_turtle(meta, sections, doc_id):
    """Return a Turtle string for a single document.

    The Turtle is built incrementally; the final triple is terminated with
    a period.
    """
    lines = [f"@prefix ex: <{BASE_IRI}> .", "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .", ""]
    doc_iri = f"{BASE_IRI}Document{doc_id}"
    lines.append(f"<{doc_iri}> a ex:Document ;")
    # Title
    title = meta.get("title", "")
    lines.append(f"  ex:hasTitle \"{title}\" ;")
    # Category
    category = meta.get("category", "")
    lines.append(f"  ex:hasCategory \"{category}\" ;")
    # Status
    status = meta.get("status", "")
    lines.append(f"  ex:hasStatus \"{status}\" ;")
    # Keywords
    for kw in meta.get("keywords", []):
        lines.append(f"  ex:hasKeyword \"{kw}\" ;")
    # Sections
    for idx, sec in enumerate(sections, start=1):
        sec_hash = sha1(sec)
        sec_iri = f"{BASE_IRI}Section_{sec_hash}"
        lines.append(f"  ex:hasSection <{sec_iri}> ;")
        # Section node definition
        lines.append(f"<{sec_iri}> a ex:Section ;")
        lines.append(f"  ex:sectionTitle \"{sec}\" ;")
        lines.append(f"  ex:sectionOrder {idx} ;")
        lines[-1] = lines[-1].rstrip(" ;") + " ."
    # Related artifacts
    for rel in meta.get("related", []):
        rel_iri = f"{BASE_IRI}Document{rel}"
        lines.append(f"  ex:hasRelatedArtifact <{rel_iri}> ;")
    # Finalize the document triple
    lines[-1] = lines[-1].rstrip(" ;") + " ."
    return "\n".join(lines)


def post_turtle(turtle_str):
    """POST a Turtle fragment to GraphDB."""
    headers = {"Content-Type": "text/turtle"}
    resp = requests.post(GRAPHDB_URL, data=turtle_str.encode("utf-8"), headers=headers)
    resp.raise_for_status()

# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def main():
    if not CLONE_DIR.exists():
        print(f"Clone directory {CLONE_DIR} does not exist. Exiting.", file=sys.stderr)
        sys.exit(1)
    md_files = list(CLONE_DIR.rglob("*.md"))
    if not md_files:
        print("No Markdown files found.")
        return
    for md_path in md_files:
        try:
            meta, sections = parse_markdown(md_path)
        except Exception as exc:
            print(f"Skipping {md_path}: {exc}", file=sys.stderr)
            continue
        doc_id = sha1(md_path.as_posix())
        turtle = build_turtle(meta, sections, doc_id)
        try:
            post_turtle(turtle)
        except Exception as exc:
            print(f"Failed to POST {md_path}: {exc}", file=sys.stderr)
            continue
        print(f"Ingested {md_path}")

if __name__ == "__main__":
    main()
