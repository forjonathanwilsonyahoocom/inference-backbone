from datetime import datetime
from contracts.inference_contracts.validations import ArtifactId
from pydantic import BaseModel

class Task(BaseModel):
    task_id: ArtifactId
    execution_id: str
    instance_number: int # numbering within the execution

    content: str
    content_hash: str | None = None

    model_name: str
    
    observed_at: datetime
