from fastapi import FastAPI

app = FastAPI()


from routers.health import health_router
from routers.ingest_evidence import ingest_evidence_router
from routers.ingest_claim import ingest_claim_router
from routers.search import search_router
from routers.retrieval import retrieval_router

app = FastAPI()

app.include_router(health_router)
app.include_router(ingest_evidence_router)
app.include_router(ingest_claim_router)
app.include_router(search_router)
app.include_router(retrieval_router)
