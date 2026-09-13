from fastapi import APIRouter

health_router = APIRouter()

@health_router.get("/health")
async def health_route():
    return {"status": "ok with new content"}
