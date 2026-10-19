
# compressors.py
"""Utility functions to compress tool outputs before sending back to the LLM.

Each tool namespace can provide a custom compressor that reduces the size of the
payload while preserving the essential information needed for downstream
processing.  The compressor is a simple callable that accepts the raw tool
result and returns a lightweight representation.

The mapping is intentionally minimal – only the tools that are known to produce
large payloads are included.  If a tool is not in the mapping, its output is
returned unchanged.
"""

from typing import Any, Callable, Dict, Set
from toolbox.run_command import compress_run_command
from toolbox.search_file import compress_search_file
from toolbox.search_evidence import compress_search_evidence, search_evidence
from toolbox.web_search import compress_web_search
from toolbox.web_fetch import compress_web_fetch
from toolbox.run_in_workspace import compress_run_in_workspace
from toolbox.read_file import compress_read_file
from agent.models import Iteration, AgentRequest


from observability.metrics import MetricsWrapper
from langchain_core.messages import AIMessage
from toolbox.util import middle_slice, clip_mid
import json

# ---------------------------------------------------------------------------
# Compressor implementations
# ---------------------------------------------------------------------------

# Mapping from tool name to compressor callable
COMPRESSORS: Dict[str, Callable[[Any, int], Any]] = {
    "read_file": compress_read_file,
    "run_command": compress_run_command,
    "search_file": compress_search_file,
    "search_evidence": compress_search_evidence,
    "web_search": compress_web_search,
    "web_fetch": compress_web_fetch,
    "run_in_workspace" : compress_run_in_workspace,
}

# Helper to get a compressor or identity

def get_compressor(tool_name: str) -> Callable[[Any], Any]:
    return COMPRESSORS.get(tool_name, lambda x, y: x)

TRY_SEMANTIC_COMPRESSOR: Set[str] = {"read_file", "web_fetch", "run_in_workspace"}

def get_tool_call_purpose(resp: AIMessage):
    purpose = []
    for tc in resp.tool_calls or []:
        purpose.append(tc.get("args", {}).get("purpose", ""))
    return " ".join(purpose).strip() 
    
def semantic_compressor(config: AgentRequest, metrics: MetricsWrapper, it: Iteration, limit: int) -> str | None:
    if it.tool_name in TRY_SEMANTIC_COMPRESSOR and it.tool_call_result_chunks is None: 
        try:
            # Determine how many chunks to fetch based on tier limit
            #find largest just in case someone is testing a non linear arrangement
            largest_tier_limit = 0
            for t in config.compression_tiers:
                if largest_tier_limit < t[1]:
                    largest_tier_limit = t[1]
                    
            num_chunks = largest_tier_limit // 1000 #match with backbone-api chunk size
            purpose = get_tool_call_purpose(it.model_response)
            print(f"semantic compressor purpose: {purpose}")
            if(purpose):
                args = {"purpose" : "find compression chunks", 
                        "query" : purpose, 
                        "limit" : num_chunks + 1, 
                        "instance_number" : it.tool_call_result_instance_number, 
                        "execution_id" : config.execution_id}
                raw_chunks = search_evidence.invoke(args)
                chunks = json.loads(raw_chunks)
                it.tool_call_result_chunks = chunks
            
            metrics.emit(metrics.get_counter_message("compression_semantic_compressor_got_chunks", "compression event"))
        except Exception as e:
            print(e)
            metrics.emit(metrics.get_counter_message("compression_semantic_compressor_error", "failed to fetch evidence chunks")) 
    
    compressed_result = None
    if it.tool_call_result_chunks is not None:
        # Build compressed string from chunks up to limit
        compressed_chunks = []
        re_ordered_chunks = []
        remaining_limit = limit
        min_distance = it.tool_call_result_chunks[0]["distance"]
        for i, stored_chunk in enumerate(it.tool_call_result_chunks):
            if "content" in stored_chunk["properties"]:
                remaining_limit -= len(stored_chunk["properties"]["content"])
                if remaining_limit <=0 and i > 0: #first collect at least one of the closest chunks
                    #do not collect additional chunks after the closest if they exceed limit
                    break
                re_ordered_chunks.append(stored_chunk)
            
        #then sort them in the order they occur in the result
        re_ordered_chunks.sort(key=lambda x: x['properties']['chunk_index'])
        
        next_expected = 0
        done = False
        for i, stored_chunk in enumerate(it.re_ordered_chunks):
            if done == True:
                break
            chunk = stored_chunk["properties"]["content"]
            chunk_tag = ""
            omitted = 0
            #derive the omitted section length
            if next_expected < stored_chunk['properties']['chunk_index']:
                omitted = (re_ordered_chunks[0]['properties']['chunk_index'] - next_expected) * 700 #tune with backbone-api chunk size
                
            if next_expected == stored_chunk['properties']['chunk_index'] and next_expected > 0:
                #slice off the overlap from this chunk
                chunk = chunk[200:]
                
            so_far = len("\n".join(compressed_chunks))
            if limit - so_far <= 0:
                break
                
            if so_far + len(chunk) > limit and i == 0:
                chunk_middle = middle_slice(chunk, limit - so_far)
                omitted += len(chunk) - len(chunk_middle)
                chunk = chunk_middle
                done = True
                
            if ommited > 0:
                omitted_tag =  f"...omitted approx {omitted} chars ... \n "
                #chunk count is 1 based, chunk index is 0 based
                chunk_tag = f"{ommited}chunk {chunk.get('chunk_index', 0) + 1} of {chunk.get('chunk_count', 0)}:"
            
            compressed_chunks.append(f"{chunk_tag}{chunk}")
            next_expected = stored_chunk['properties']['chunk_index'] + 1
            
        #derive approximate amount of truncation
        if next_expected < it.tool_call_result_chunks[0]['properties']['chunk_count']:
            compressed_chunks.append(f"...truncated approx {(it.tool_call_result_chunks[0]['properties']['chunk_count'] - next_expected) * 700 } chars") 
            
        compressed_result = "\n".join(compressed_chunks).strip()
        
        metrics.emit(metrics.get_counter_message("compression_semantic_compressor_compressed", "compression event"))
        print(f"semantic compressor found: \n {compressed_result}")
        if len(compressed_result) == 0:
            compressed_result = None
        
    return compressed_result


"""End of compressors.py"""




