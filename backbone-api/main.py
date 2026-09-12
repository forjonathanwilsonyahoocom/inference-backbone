from fastapi import FastAPI

app = FastAPI()


from routers.health import health_router
from routers.ingest import ingest_router
from routers.search import search_router

app = FastAPI()

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(search_router)
