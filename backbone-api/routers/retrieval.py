# inference-backbone/backbone-api/routers/retrieval.py

import json
from pathlib import Path

import anyio
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

# Base directory where artifacts are stored
BASE_DIR = Path("/indexed-artifacts")

# Allowed document types based on contracts
ALLOWED_DOC_TYPES = {"claim", "evidence"}

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
    ``{execution_id}-{iteration}.json`` and returns the sorted list of
    identifiers.
    """
    if doc_type not in ALLOWED_DOC_TYPES:
        return {"error": f"unknown doc_type: {doc_type}"}

    import re
    evidence_dir = BASE_DIR / doc_type
    if not evidence_dir.exists():
        return {"error": f"{doc_type} directory not found"}

    pattern = re.compile(rf"^{re.escape(execution_id)}-(\d+)\.json$")
    files = []
    for f in evidence_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            iteration = int(m.group(1))
            files.append((iteration, f.name))
    files.sort(key=lambda x: x[0])
    evidence_ids = [name.split(".")[0] for _, name in files]
    return {
        "execution_id": execution_id,
        "evidence_ids": evidence_ids,
    }
