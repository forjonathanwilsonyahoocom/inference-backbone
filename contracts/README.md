# Contracts Package

The **contracts** package defines the Pydantic data models that are shared across all services. These contracts describe the shape of requests, responses, and domain objects used by the worker, validator, and backbone APIs.

## Sub‑packages

| Package | Purpose |
|---------|---------|
| `general_contracts` | Generic request/response models (e.g., `RunRequest`, `RunResponse`, `SearchRequest`). |
| `inference_contracts` | Domain models for the inference pipeline (e.g., `AgentState`, `Episode`, `Claim`, `Evidence`). |
| `validation_contracts` | Models for the validation phase (e.g., `SupportEntry`, `ValidationResult`). |
| `inference_contracts` | Additional inference‑specific contracts (e.g., `Task`, `FinalAnswer`). |

## Example contract

```python
class AgentRequest(BaseModel):
    mode: Literal["worker_tools", "knowledge_tools"]
    worker_model: str
    worker_temp: float
    worker_num_ctx: int
    distillation_model: str
    distillation_temp: float
    distillation_num_ctx: int
    base_url: str
```

## Usage

All services import the contracts via relative imports, e.g., `from contracts.inference_contracts.agent_state import AgentState`.

---

See the source files in `contracts/` for the full list of models.
