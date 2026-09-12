from pydantic import BaseModel

class EvidenceChunk(BaseModel):
    """Projection of :class:`Evidence` for storage in the vector store.

    Only the fields required by the vector store are kept.  The ``id`` is
    preserved so that we can round‑trip back to the original :class:`Evidence`.
    """
    id: str
    text: str

    class Config:
        frozen = True
