# inference-backbone/backbone-api/routers/retrieval.py
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pathlib import Path


BASE_DIR = Path("/indexed-artifacts")

retrieval_router = APIRouter()

@retrieval_router.get("/file/evidence/{event_id}")
async def get_evidence_file(event_id: str):
    store_path = BASE_DIR / "evidence"
    file_path = store_path / f"{event_id}.json"
    if not file_path.exists():
        return {"error": "file not found"}
    return FileResponse(path=str(file_path), media_type="application/json")


@retrieval_router.get("/list/evidence/{execution_id}")
async def list_evidence_files(execution_id: str):
    """Return a list of evidence event IDs for a given execution, ordered by iteration.

    The evidence files are stored under ``BASE_DIR / "evidence"`` and named
    ``{execution_id}-{iteration}.json``.  This endpoint scans that directory,
    extracts the iteration number, sorts the files, and returns a JSON payload
    containing the ordered list of event IDs.
    """
    import re
    evidence_dir = BASE_DIR / "evidence"
    if not evidence_dir.exists():
        return {"error": "evidence directory not found"}
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

