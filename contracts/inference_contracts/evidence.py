from pydantic import BaseModel

class Evidence(BaseModel):
    """Canonical domain model for evidence.

    The model is intentionally minimal – it captures the identity of an
    evidence item and the raw text that will be stored in the vector store.
    Additional metadata can be added later without breaking the contract.
    """
    id: str
    text: str

    class Config:
        frozen = True
        json_schema_extra = {
            "title": "Evidence",
            "description": "Domain model representing a piece of evidence.",
        }
