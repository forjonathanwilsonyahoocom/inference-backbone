import json
import os
import requests
from observability.metrics import MetricsWrapper
from fastapi import FastAPI
from pydantic import BaseModel

from contracts.inference_contracts.claim import Claim
from prometheus_client import start_http_server
from langchain_ollama import ChatOllama
from agent.telemetry import fetch_events
from agent.episode import extract_episode

from typing import List
from agent.loop import handle_claims_extraction, handle_validation
from contracts.general_contracts.text_analysis import ReportForEpisodeExtraction
from contracts.inference_contracts.episode import Episode

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
    execution_id: str

class ValidateRequest(BaseModel):
    execution_id: str
    
app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/extract_claims")
async def extract_claims(req: ClaimsRequest):
    config = get_ollama_config()
    llm = create_llms(config)
    
    task_events = await fetch_events("task", req.execution_id)
    final_answer_events = await fetch_events("final_answer", req.execution_id)
    
    # Assuming the first element contains the required content
    task_content = task_events[0].get("content", "No task content found.") if task_events else "No task content found."
    final_answer_content = final_answer_events[0].get("content", "No final answer content found.") if final_answer_events else "No final answer content found."
    
    user_content = f"TASK:\n{task_content}\n\nFINAL RESPONSE:\n{final_answer_content}"
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
    
    claim_events = await fetch_events("claim", req.execution_id)
    # Convert event dicts to Claim objects
    claims_list = [Claim(**e) for e in claim_events]
    
    result = await handle_validation(
        config=config,
        metrics=METRICS,
        llm = llm, 
        claims_list = claims_list,
        execution_id = req.execution_id
    )
    return result
    

@app.post("/make_episode")
async def validate(req: ReportForEpisodeExtraction):
    config = get_ollama_config()
    llm = create_llms(config)
    episode_llm = llm.with_structured_output(Episode)
    result = await extract_episode(
        config=config,
        metrics=METRICS,
        llm = episode_llm, 
        req = req
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
