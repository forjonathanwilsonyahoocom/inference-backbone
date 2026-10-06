import os
import sys
import importlib.util
import sys
sys.path.append("../agent")
import types
import pytest

# Load run_agent from worker-agent module
spec = importlib.util.spec_from_file_location(
    "loop_module",
    "worker-agent/app/agent/loop.py"
)
loop_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop_module)
run_agent = loop_module.run_agent

# Dummy MetricsWrapper that records emits
class DummyMetrics:
    def __init__(self):
        self.emitted = []
    def emit(self, msg):
        self.emitted.append(msg)

# Dummy LLM that returns a response object
class DummyResponse:
    def __init__(self, content="", tool_calls=None, usage_metadata=None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage_metadata = usage_metadata or {}

class DummyLLM:
    def __init__(self, response):
        self.response = response
    def invoke(self, messages):
        # ignore messages, just return the preset response
        return self.response

# Dummy distillation LLM (unused in this test)
class DummyDistillLLM:
    def invoke(self, messages):
        return DummyResponse(content="{}")

# Helper to create config dict
config = {
    "model": "dummy-model",
    "distill_model": "dummy-distill",
}

# Test that run_agent returns expected result when no tool calls

def test_run_agent_no_tool_calls():
    metrics = DummyMetrics()
    # Response with content and no tool calls
    response = DummyResponse(content="Hello world", tool_calls=[])
    llm = DummyLLM(response)
    distill_llm = DummyDistillLLM()
    tools = {}  # no tools
    user_request = "Say hello"
    execution_id = "test-exec-123"
    result = run_agent(
        metrics=metrics,
        config=config,
        tools=tools,
        llm_with_tools=llm,
        distillation_llm=distill_llm,
        user_request=user_request,
        execution_id=execution_id,
        max_iterations=5,
        verbose=False,
    )
    # Check final response
    assert result["final_response"] == "Hello world"
    # No events should be recorded
    assert result["events"] == []
    # Iterations should be 1
    assert result["iterations"] == 1
    # Execution id matches
    assert result["execution_id"] == execution_id
    # Metrics should have emitted start and completed operation counters
    operation_labels = [m for m in metrics.emitted if m.get("name") == "operation"]
    assert len(operation_labels) >= 2
    # The first should have operation 'begin loop', the second 'completed'
    ops = [m.get("labels", {}).get("operation") for m in operation_labels]
    assert "begin loop" in ops
    assert "completed" in ops

# Test that run_agent handles unknown tool gracefully

def test_run_agent_unknown_tool():
    metrics = DummyMetrics()
    # Response with a tool call that is unknown
    response = DummyResponse(content="", tool_calls=[{"name": "unknown_tool", "args": {"x": 1}, "id": "1"}])
    llm = DummyLLM(response)
    distill_llm = DummyDistillLLM()
    tools = {}  # no known tools
    user_request = "Call unknown tool"
    execution_id = "test-exec-456"
    result = run_agent(
        metrics=metrics,
        config=config,
        tools=tools,
        llm_with_tools=llm,
        distillation_llm=distill_llm,
        user_request=user_request,
        execution_id=execution_id,
        max_iterations=3,
        verbose=False,
    )
    # After unknown tool, the agent should eventually finish with no tool calls
    assert result["condition"] == "no tool calls" or result["condition"].startswith("Agent stopped")
    # There should be at least one event recorded for the unknown tool call
    assert any(e["event_type"] == "tool_call_result" for e in result["events"])
    # The result of the tool call should indicate unknown tool
    assert any("Unknown tool" in e["result"] for e in result["events"])

# Test that run_agent respects max_iterations

def test_run_agent_max_iterations():
    metrics = DummyMetrics()
    # Response that always returns a tool call, causing loop to iterate
    response = DummyResponse(content="", tool_calls=[{"name": "unknown_tool", "args": {}, "id": "1"}])
    llm = DummyLLM(response)
    distill_llm = DummyDistillLLM()
    tools = {}  # no known tools
    user_request = "Keep looping"
    execution_id = "test-exec-789"
    max_iter = 2
    result = run_agent(
        metrics=metrics,
        config=config,
        tools=tools,
        llm_with_tools=llm,
        distillation_llm=distill_llm,
        user_request=user_request,
        execution_id=execution_id,
        max_iterations=max_iter,
        verbose=False,
    )
    # Should stop after max_iterations
    assert result["iterations"] == max_iter
    assert result["condition"].startswith("Agent stopped after")

