"""FastAPI application entry point.

The original project exposed a single ``/ingest`` endpoint that
handled markdown documents.  For the new memory ingestion flow we
add a dedicated router that implements the ``POST /memory/ingest``
endpoint described in the specification.

The router is mounted in :mod:`inference_backbone.fastapi.main`.
"""

from fastapi import FastAPI

from inference_backbone.fastapi.memory_ingest import router as memory_ingest_router
from inference_backbone.fastapi.memory_search import router as memory_search_router

app = FastAPI()
app.include_router(memory_search_router)
app.include_router(memory_ingest_router)

# The original /ingest endpoint is still available via the
# ``main`` module.  Importing it here keeps backward compatibility
# for any existing tests that rely on the old behaviour.
from inference_backbone.fastapi.main import ingest as old_ingest

app.post("/ingest")(old_ingest)

# Health endpoint for liveness checks
@app.get("/health")
async def health():
    return {"status": "ok"}

# End of module
