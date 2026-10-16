from typing import Tuple, List
from pydantic import BaseModel

from langchain_ollama import ChatOllama

from prometheus_client import start_http_server
from fastapi import FastAPI

from agent.loop import run_agent
from agent.models import AgentRequest
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
from toolbox.run_in_workspace import run_in_workspace

from contracts.inference_contracts.agent_state import AgentState

METRICS = None #this global is instantiated during app startup, a reference is sent to the agent runtime
    
def init_metrics() -> MetricsWrapper:
    metrics = MetricsWrapper("worker-agent")
    return metrics

def create_llms(config: AgentRequest) -> Tuple[ChatOllama, ChatOllama]:
    llm = ChatOllama(
        model=config.worker_model,
        base_url=config.base_url,
        temperature=config.worker_temp,
        num_ctx=config.worker_num_ctx,
    )
    distill_llm = ChatOllama(
        model=config.distillation_model,
        base_url=config.base_url,
        temperature=config.distillation_temp,
        num_ctx=config.distillation_num_ctx,
    )
    return llm, distill_llm

def get_toolchain(llm: ChatOllama) -> Tuple[dict, ChatOllama]:
    TOOLS = [list_files, read_file, write_file, edit_file,
             search_file, search_evidence, run_command, web_search, web_fetch, run_in_workspace]
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


@app.post("/run")
async def run_agent_endpoint(config: AgentRequest):
    llm, distill_llm = create_llms(config)
    distill_llm_typed = distill_llm.with_structured_output(AgentState)
    tools, llm_with_tools = get_toolchain(llm)
    METRICS.clear_counters()
    result = run_agent(
        metrics=METRICS,
        config=config,
        tools=tools,
        llm_with_tools=llm_with_tools,
        distillation_llm=distill_llm_typed
    )
    return result

@app.get("/health")
def health():
    return {"status": "ok"}

