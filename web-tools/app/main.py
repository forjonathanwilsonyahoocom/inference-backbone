import os
import uuid

from typing import Tuple, List, Dict
from pydantic import BaseModel
from contracts.general_contracts.comms import WebSearchRequest, WebFetchRequest

from prometheus_client import start_http_server
from fastapi import FastAPI

from observability.metrics import MetricsWrapper

from toolbox.web_search import web_search
from toolbox.web_fetch import web_fetch

METRICS = None #this global is instantiated during app startup
operation_metric_labeler = None
def init_metrics() -> MetricsWrapper:
    metrics = MetricsWrapper("web-tools")
    global operation_metric_labeler
    operation_metric_labeler = metrics.get_counter_message_labeler(
        "operation", "web-tools general activity"
    )
    return metrics

app = FastAPI()

# FastAPI startup hook
@app.on_event("startup")
def startup_event():
    global METRICS
    METRICS = init_metrics()
    METRICS.emit(operation_metric_labeler({"operation": "startup"}))
    start_http_server(8080)

@app.post("/fetch")
async def fetch(payload: WebFetchRequest) -> Dict:
    result = await web_fetch(payload.url)
    METRICS.emit(operation_metric_labeler({"operation": "fetch"}))
    return result

@app.post("/search")
async def search(payload: WebSearchRequest) ->  List[Dict]:
    result = await web_search(payload.query)
    METRICS.emit(operation_metric_labeler({"operation": "search"}))
    return result

@app.get("/health")
def health():
    return {"status": "ok"}

