from agent.compression import clip_mid, compress_args, compress_response, compress_history
from agent.models import Iteration, ToolCallResultWrapper, materialize_agent_request
from contracts.inference_contracts.worker_agent_request import AgentRequest
from observability.metrics import MetricsWrapper
from langchain_core.messages import AIMessage
from typing import List
import pytest

@pytest.fixture
def mock_metrics():
    return MetricsWrapper("test", is_mock=True)

@pytest.fixture
def mock_config():
    # Default config for testing compression
    return materialize_agent_request(AgentRequest(request="test",
                         base_url="somewhere",
                         mode="worker_tools",
                         distill_at=10000,
                         compression_tiers=[(0, 1000), (10, 500)]))
    
def test_clip_mid_basic(mock_metrics: MetricsWrapper):
    # Test simple clipping
    long_string = "A" * 200
    limit = 50
    omitted_marker_approximate_len = 30
    clipped = clip_mid(mock_metrics, long_string, limit)
    assert len(clipped) <= limit+ omitted_marker_approximate_len
    # Based on limit=50 and marker_length=26, the maximum head possible while keeping tail>=1 is 23.
    assert clipped.startswith("A" * 23) 
    assert "..." in clipped

def test_clip_mid_no_clipping(mock_metrics: MetricsWrapper):
    # Test when length is within limit
    short_string = "short"
    limit = 10
    clipped = clip_mid(mock_metrics, short_string, limit)
    assert clipped == short_string

def test_compress_args_tool_call_structure(mock_metrics: MetricsWrapper):
    # Test compression specifically for tool call arguments (nested dict)
    args = {"arg1": "X" * 100, "nested_arg": {"sub_key": "Y" * 100}}
    limit = 30
    compressed = compress_args(mock_metrics, args, limit)
    assert isinstance(compressed, dict)
    assert "..." in compressed["arg1"]
    assert "..." in compressed["nested_arg"]["sub_key"]

def test_compress_response_with_tool_calls(mock_metrics: MetricsWrapper):
    # Test response compression including tool calls
    long_content = "A" * 300
    ai_message = AIMessage(content=long_content, tool_calls=[
        {"id": "tc1", "name": "tool_a", "args": {"arg1": "long arg content for tool a" + "long" * 20 }},
        {"id": "tc2", "name": "tool_b", "args": {"arg2": "another long arg content for tool b"}}
    ])
    limit = 50
    omitted_marker_approximate_len = 30
    compressed_message = compress_response(mock_metrics, ai_message, limit)
    
    assert isinstance(compressed_message, AIMessage)
    assert len(compressed_message.content) <= limit+ omitted_marker_approximate_len
    assert "..." in compressed_message.content
    assert len(compressed_message.tool_calls) == 2
    
    # Check tool call argument compression
    tc1 = compressed_message.tool_calls[0]
    assert "..." in tc1["args"]["arg1"]

def test_compress_history_basic(mock_metrics: MetricsWrapper, mock_config: AgentRequest):
    # Test basic history compression flow
    mock_iteration = Iteration(iteration=10, step_fingerprint="fp1", model_response=AIMessage(content="A" * 500), tool_call_results=[
        ToolCallResultWrapper(
            tool_call_id = "1",
            tool_call_result= "B" * 500,
            tool_call_result_utility = 0.9,
            tool_call_fingerprint = 'fp_tc1',
            result_fingerprint =  'fp_res1',
            tool_call_result_instance_number=  1
        )
    ])
    history: List[Iteration] = [mock_iteration]
    
    # Mock compression logic to ensure it runs and returns modified history
    # Note: Since we cannot mock internal functions like semantic_compressor easily here, 
    # we test the structural integrity and flow.
    compressed_history = compress_history(mock_config, mock_metrics, history, upto=0)
    
    # Check if compression flags were set (e.g., model_response_compressed)
    assert hasattr(compressed_history[0], 'model_response_compressed')
    assert hasattr(compressed_history[0], 'compression_limit')
    
def test_compress_history_no_compression_due_to_limit(mock_metrics: MetricsWrapper, mock_config: AgentRequest):
    # Test case where limit is high or compression_limit matches limit
    mock_iteration = Iteration(iteration=10, step_fingerprint="fp1", model_response=AIMessage(content="A" * 10), tool_call_results=[
        ToolCallResultWrapper(
            tool_call_id = "1",
            tool_call_result= "B" * 10,
            tool_call_result_utility = 1.0,
            tool_call_fingerprint = 'fp_tc1',
            result_fingerprint =  'fp_res1',
            tool_call_result_instance_number=  1
        )
    ])
    history: List[Iteration] = [mock_iteration]
    
    # Set a high compression limit that won't trigger clipping
    mock_config.compression_tiers = [(0, 10000)]
    
    compressed_history = compress_history(mock_config, mock_metrics, history, upto=0)
    
    # Ensure compression flags are still set but don't indicate clipping occurred
    assert hasattr(compressed_history[0], 'model_response_compressed')
    assert compressed_history[0].compression_limit == 10000
