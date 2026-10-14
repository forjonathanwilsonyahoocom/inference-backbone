from pydantic import BaseModel

class InfoChunk(BaseModel):
    chunk_id: str | None = None #a content based uuid
    execution_id: str #everything comes from executions
    source_id: str #the id of the source this was derived from
    item_id: str | None #id assigned to derived item 
    info_type: str #the source object type
    instance_number_start: int | None = None #only used as lower bound when range of iterations results in this
    instance_number: int # source object numbering within the execution
    
    content: str

    chunk_index: int
    chunk_count: int

    embedding_model: str | None = None

