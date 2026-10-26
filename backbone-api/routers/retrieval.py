# inference-backbone/backbone-api/routers/retrieval.py

import json
from pathlib import Path
import re
import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from util.sorting import sort_identifiers

# Base directory where artifacts are stored
BASE_DIR = Path("/indexed-artifacts")

# Allowed document types based on contracts
ALLOWED_DOC_TYPES = {"claim", "evidence", "claim_evidence_edge", "agent_state", "final_answer", "task"}

retrieval_router = APIRouter()

def find_document_path(doc_type: str, identifier: str) -> Path | None:
    if doc_type not in ALLOWED_DOC_TYPES:
        return None

    # identifier must be a filename stem, not a path
    if (
        not identifier
        or "/" in identifier
        or "\\" in identifier
        or identifier in {".", ".."}
    ):
        return None

    file_path = BASE_DIR / doc_type / f"{identifier}.json"

    try:
        file_path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        return None

    return file_path if file_path.is_file() else None


@retrieval_router.get("/file/{doc_type}/{identifier}")
async def get_document_file(doc_type: str, identifier: str):
    """Return a single document file for external callers.

    Parameters
    ----------
    doc_type: str
        One of the allowed document types.
    identifier: str
        The filename (without extension) of the stored JSON.
    """
    
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown doc_type: {doc_type}",
        )

    file_path = find_document_path(doc_type, identifier)

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return FileResponse(
        path=file_path,
        media_type="application/json",
    )


async def load_document(doc_type: str, identifier: str) -> dict:
    """Return a single document file for internal callers.

    Parameters
    ----------
    doc_type: str
        One of the allowed document types.
    identifier: str
        The filename (without extension) of the stored JSON.
    """

    if doc_type not in ALLOWED_DOC_TYPES:
        raise ValueError(f"Unknown doc_type: {doc_type}")

    file_path = find_document_path(doc_type, identifier)

    if file_path is None:
        raise FileNotFoundError(
            f"Document not found: {doc_type}/{identifier}"
        )

    async with await anyio.open_file(
        file_path,
        mode="r",
        encoding="utf-8",
    ) as file:
        contents = await file.read()

    return json.loads(contents)
    

@retrieval_router.get("/list/{doc_type}/{execution_id}")
async def list_document_files(doc_type: str, execution_id: str):
    """Return a list of document identifiers for a given execution.

    The function scans the directory ``BASE_DIR / doc_type`` for files named
    ``{execution_id}-{iteration}.*`` and returns the sorted list of
    identifiers.
    """
    if doc_type not in ALLOWED_DOC_TYPES:
        return {"error": f"unknown doc_type: {doc_type}"}

    
    evidence_dir = BASE_DIR / doc_type
    if not evidence_dir.exists():
        return {"error": f"{doc_type} directory not found"}

    
    files = [str(file) for file in evidence_dir.glob(f"{execution_id}-*.*") if file.is_file()]
    
    evidence_ids = [name.split(".")[0] for _, name in files]
    evidence_ids = sort_identifiers(evidence_ids)
    return {
        "execution_id": execution_id,
        "evidence_ids": evidence_ids,
    }
    

@retrieval_router.get("/full_trace/{execution_id}")
async def list_full_trace_files(execution_id: str) -> dict:
    """Return a list of all document identifiers with types for a given execution.

    The function recursively scans the directory ``BASE_DIR`` for files named
    ``{execution_id}*.*`` and returns the sorted list of
    identifiers.
    """
    
    files = [file for file in BASE_DIR.rglob(f"{execution_id}-*.*") if file.is_file()]
    trace_parts = {}
    for file in files:
        parts = str(file).split("/")
        target = trace_parts.get(parts[-2], [])
        target.append(parts[-1].split(".")[0])
        trace_parts[parts[-2]] = target
    
    for k in trace_parts.keys()
        trace_parts[k] = sort_identifiers(trace_parts[k])
        
    return {
        "execution_id": execution_id,
        "nodes": trace_parts,
    }
