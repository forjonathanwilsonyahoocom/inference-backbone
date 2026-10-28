from langchain_core.messages import SystemMessage, HumanMessage
from prompts.episode import EPISODE_PROMPT
from observability.metrics import MetricsWrapper
import json
from typing import Dict, List
from langchain_ollama import ChatOllama

from contracts.general_contracts.text_analysis import ReportForEpisodeExtraction
from contracts.inference_contracts.episode import Episode


    
async def extract_episode(config: dict, 
                          metrics: MetricsWrapper, 
                          llm: ChatOllama,
                          req: ReportForEpisodeExtraction) -> Episode | None:
                          
    failure_metric_labeler = metrics.get_counter_message_labeler("error", "encountered error")
    operation_metric_labeler = metrics.get_counter_message_labeler("operation", "agent general activity")

    metrics.emit(operation_metric_labeler({"operation" : "attempting episode generation"}))
    messages = [SystemMessage(content=EPISODE_PROMPT), HumanMessage(content=req.report)]
    result = None
    last_error = None
    for _ in range(3):
        try:
            response = await llm.ainvoke(messages)
            if not isinstance(response, Episode):
                raise ValueError(f"expected a Episode object, got {type(response).__name__}")

            metrics.emit(operation_metric_labeler({"operation" : "episode generated"}))
            return response
        except Exception as exc:
            metrics.emit(failure_metric_labeler({"failure" : "parsing error"}))
            last_error = str(exc)
    if result is None:
        metrics.emit(failure_metric_labeler({"failure" : "could not extract episode"}))
        print(f"Episode extraction failed after retries: {last_error}")
   
    
    return None
    
