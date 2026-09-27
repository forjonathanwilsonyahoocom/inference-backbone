import json
import os
import requests
from observability.metrics import MetricsWrapper
from fastapi import FastAPI
from pydantic import BaseModel

from prometheus_client import start_http_server
from langchain_ollama import ChatOllama
from agent.loop import handle_claims_extraction, handle_validation

METRICS = None #this global is instantiated during app startup, a reference is sent to the agent runtime

def init_metrics() -> MetricsWrapper:
    metrics = MetricsWrapper("validator-agent")
    return metrics
    
def get_ollama_config() -> dict:
    return {
        "base_url": os.getenv("OLLAMA_URL", "http://10.42.0.192:11434"),
        "model": os.getenv("GEN_MODEL", "gpt-oss:20b"),
    }

def create_llms(config: dict) -> ChatOllama:
    llm = ChatOllama(
        model=config["model"],
        base_url=config["base_url"],
        temperature=0.01,
        num_ctx=40960,
    )
    return llm

class ClaimsRequest(BaseModel):
    task_description: str
    final_response: str
    execution_id: str

class ValidateRequest(BaseModel):
    claims_map: dict
    execution_id: str
    
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/extract_claims")
async def extract_claims(req: ClaimsRequest):
    config = get_ollama_config()
    llm = create_llms(config)
    
    user_content = f"TASK:\n{req.task_description}\n\nFINAL RESPONSE:\n{req.final_response}"
    result = await handle_claims_extraction(
        config=config,
        metrics=METRICS,
        llm = llm, 
        user_content = user_content,
        execution_id = req.execution_id
    )
    return result
    
@app.post("/validate")
async def validate(req: ValidateRequest):
    config = get_ollama_config()
    llm = create_llms(config)
    
    result = await handle_validation(
        metrics=METRICS,
        llm = llm, 
        claims_map = req.claims_map,
        execution_id = req.execution_id
    )
    return result


# FastAPI startup hook
@app.on_event("startup")
def startup_event():
    global METRICS
    METRICS = init_metrics()
    operation_metric_labeler = METRICS.get_counter_message_labeler(
        "operation", "agent general activity"
    )
    METRICS.emit(operation_metric_labeler({"operation": "startup"}))
    start_http_server(8080)


# End of file
