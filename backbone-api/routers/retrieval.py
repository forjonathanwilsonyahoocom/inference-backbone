# inference-backbone/backbone-api/routers/retrieval.py
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pathlib import Path


BASE_DIR = Path("/indexed-artifacts")

retrieval_router = APIRouter()

@retrieval_router.get("/file/evidence/{event_id}")
async def get_evidence_file(event_id: str):
 
    store_path = BASE_DIR / "evidence"
    
    file_path =  store_path / f"{event_id}.json"

    if not file_path.exists():
        return {"error": "file not found"}
        
    return FileResponse(path=str(file_path), media_type="application/json")
