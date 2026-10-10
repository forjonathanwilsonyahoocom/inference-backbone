from pydantic import BaseModel

class InfoChunk(BaseModel):
    chunk_id: str | None = None
    execution_id: str
    source_id: str #the id of the source info
    info_type: str #the source object type
    instance_number: int # source object numbering within the execution
    
    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str | None = None

