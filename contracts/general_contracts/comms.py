from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    limit: int = 8
    execution_id: str | None = None
    event_number: int | None = None


