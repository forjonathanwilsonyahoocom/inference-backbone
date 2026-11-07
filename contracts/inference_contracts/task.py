from datetime import datetime
from contracts.inference_contracts.validations import ArtifactId
from pydantic import BaseModel

class Task(BaseModel):
    task_id: ArtifactId
    execution_id: str
    agent_request_hash: str = "" #the params of this request hashed from the persist endpoint
    instance_number: int # numbering within the execution

    content: str
    content_hash: str | None = None

    model_name: str
    
    observed_at: datetime
