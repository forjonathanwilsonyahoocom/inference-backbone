# inference-backbone/backbone-api/routers/retrieval.py
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pathlib import Path

# Base directory where artifacts are stored
BASE_DIR = Path("/indexed-artifacts")

# Allowed document types based on contracts
allowed_doc_types = {"claim", "evidence", "evidence_chunk"}

retrieval_router = APIRouter()

@retrieval_router.get("/file/{doc_type}/{identifier}")
async def get_document_file(doc_type: str, identifier: str):
    """Return a single document file.

    Parameters
    ----------
    doc_type: str
        One of the allowed document types.
    identifier: str
        The filename (without extension) of the stored JSON.
    """
    if doc_type not in allowed_doc_types:
        return {"error": f"unknown doc_type: {doc_type}"}

    store_path = BASE_DIR / doc_type
    file_path = store_path / f"{identifier}.json"
    if not file_path.exists():
        return {"error": "file not found"}
    return FileResponse(path=str(file_path), media_type="application/json")


@retrieval_router.get("/list/{doc_type}/{execution_id}")
async def list_document_files(doc_type: str, execution_id: str):
    """Return a list of document identifiers for a given execution.

    The function scans the directory ``BASE_DIR / doc_type`` for files named
    ``{execution_id}-{iteration}.json`` and returns the sorted list of
    identifiers.
    """
    if doc_type not in allowed_doc_types:
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
    event_ids = [name.split(".")[0] for _, name in files]
    return {
        "execution_id": execution_id,
        "iterations": [int(name.split('-')[-1]) for name in event_ids],
        "event_ids": event_ids,
    }
