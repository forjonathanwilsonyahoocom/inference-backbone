import os
import uuid

from typing import Tuple
from pydantic import BaseModel

from langchain_ollama import ChatOllama

from prometheus_client import start_http_server
from fastapi import FastAPI

from agent.loop import run_agent
from observability.metrics import MetricsWrapper

from toolbox.web_search import web_search
from toolbox.web_fetch import web_fetch
from toolbox.search_file import search_file
from toolbox.search_evidence import search_evidence
from toolbox.list_files import list_files
from toolbox.read_file import read_file
from toolbox.write_file import write_file
from toolbox.edit_file import edit_file
from toolbox.run_command import run_command

from prompts.distillation_schema import AgentState

METRICS = None #this global is instantiated during app startup, a reference is sent to the agent runtime

def init_metrics() -> MetricsWrapper:
    metrics = MetricsWrapper("worker-agent")
    return metrics

def get_ollama_config() -> dict:
    return {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://10.42.0.192:11434/"),
        "model": os.getenv("GEN_MODEL", "gpt-oss:20b"),
        "distill_model": os.getenv("DISTILL_GEN_MODEL", "gpt-oss:20b"),
    }

def create_llms(config: dict) -> Tuple[ChatOllama, ChatOllama]:
    llm = ChatOllama(
        model=config["model"],
        base_url=config["base_url"],
        temperature=0.01,
    )
    distill_llm = ChatOllama(
        model=config["distill_model"],
        base_url=config["base_url"],
        temperature=0.01,
    )
    return llm, distill_llm

def get_toolchain(llm: ChatOllama) -> Tuple[dict, ChatOllama]:
    TOOLS = [list_files, read_file, write_file, edit_file,
             search_file, search_evidence, run_command, web_search, web_fetch]
    llm_with_tools = llm.bind_tools(TOOLS)
    TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}
    return TOOLS_BY_NAME, llm_with_tools

app = FastAPI()

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

class AgentRequest(BaseModel):
    request: str
    max_iterations: int = 150
    execution_id: str = str(uuid.uuid4())
    verbose: bool = False    

@app.post("/run")
async def run_agent_endpoint(req: AgentRequest):
    config = get_ollama_config()
    llm, distill_llm = create_llms(config)
    distill_llm_typed = distill_llm.with_structured_output(AgentState)
    tools, llm_with_tools = get_toolchain(llm)
    
    result = run_agent(
        metrics=METRICS,
        config=config,
        tools=tools,
        llm_with_tools=llm_with_tools,
        distillation_llm=distill_llm_typed,
        user_request=req.request,
        execution_id=req.execution_id,
        max_iterations=req.max_iterations,
        verbose=req.verbose,
    )
    return result

@app.get("/health")
def health():
    return {"status": "ok"}

