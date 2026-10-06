import importlib.util
import pytest

# Load compress_history and Iteration
spec = importlib.util.spec_from_file_location(
    "compression_module",
    "inference-backbone/worker-agent/app/agent/compression.py"
)
compression_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compression_module)
compress_history = compression_module.compress_history
limit_for_age = compression_module.limit_for_age
clip_mid = compression_module.clip_mid
compress_response = compression_module.compress_response

# Load Iteration model
spec_iter = importlib.util.spec_from_file_location(
    "iteration_module",
    "inference-backbone/worker-agent/app/agent/models.py"
)
iteration_module = importlib.util.module_from_spec(spec_iter)
spec_iter.loader.exec_module(iteration_module)
Iteration = iteration_module.Iteration

# Dummy metrics wrapper that records emitted messages
class DummyMetrics:
    def __init__(self):
        self.emitted = []
    def emit(self, msg):
        self.emitted.append(msg)

# Helper to create a large string
large_text = "x" * 2000

# ---------------------------------------------------------------------------
# Tests for limit_for_age
# ---------------------------------------------------------------------------

def test_limit_for_age():
    # Age 0 -> None
    assert limit_for_age(0) is None
    # Age 5 -> 600 (since 5 >= 4 but <10)
    assert limit_for_age(5) == 600
    # Age 10 -> 600 (since 10 >=10)
    assert limit_for_age(10) == 600
    # Age 15 -> 600
    assert limit_for_age(15) == 600

# ---------------------------------------------------------------------------
# Tests for clip_mid
# ---------------------------------------------------------------------------

def test_clip_mid_short():
    metrics = DummyMetrics()
    result = clip_mid(metrics, "short", 10)
    assert result == "short"
    assert not metrics.emitted


def test_clip_mid_long():
    metrics = DummyMetrics()
    long = "a" * 100
    result = clip_mid(metrics, long, 20)
    # Should be head+tail with omitted marker
    assert "...[" in result
    assert result.startswith("a" * 14)  # 70% of 20 = 14
    assert result.endswith("a" * 6)
    # Check emitted counter
    assert any(msg.get("name") == "compression_amount" for msg in metrics.emitted)

# ---------------------------------------------------------------------------
# Tests for compress_response
# ---------------------------------------------------------------------------

def test_compress_response_no_tool_calls():
    from langchain_core.messages import AIMessage
    metrics = DummyMetrics()
    msg = AIMessage(content="x" * 50)
    compressed = compress_response(metrics, msg, 20)
    assert compressed.content == clip_mid(metrics, msg.content, 20)
    assert compressed.tool_calls == []


def test_compress_response_with_tool_calls():
    from langchain_core.messages import AIMessage
    metrics = DummyMetrics()
    msg = AIMessage(content="x" * 50, tool_calls=[{
        "id": "1",
        "name": "test",
        "args": {"param": "a" * 100},
        "type": "tool_call"
    }])
    compressed = compress_response(metrics, msg, 20)
    # content clipped
    assert compressed.content == clip_mid(metrics, msg.content, 20)
    # args clipped
    assert compressed.tool_calls[0]["args"]["param"] == clip_mid(metrics, msg.tool_calls[0]["args"]["param"], 20)

# ---------------------------------------------------------------------------
# Tests for compress_history
# ---------------------------------------------------------------------------

def test_compression_without_tool_name():
    metrics = DummyMetrics()
    it = Iteration(iteration=1, tool_name=None, tool_call_result=large_text, model_response=None)
    history = [it]
    compress_history(metrics, history, upto=0)
    assert it.tool_call_result_compressed == large_text
    assert all(msg.get("name") != "compression_compressed" for msg in metrics.emitted)


def test_compression_with_read_file_tool():
    metrics = DummyMetrics()
    it_new = Iteration(iteration=10, tool_name="read_file", tool_call_result=large_text, model_response=None)
    it_old = Iteration(iteration=5, tool_name="read_file", tool_call_result=large_text, model_response=None)
    history = [it_old, it_new]
    compress_history(metrics, history, upto=0)
    # Older iteration compressed
    assert it_old.compression_limit is not None
    assert it_old.tool_call_result_compressed != large_text
    # Newer iteration unchanged
    assert it_new.tool_call_result_compressed is None
    # Counter emitted once
    assert sum(1 for msg in metrics.emitted if msg.get("name") == "compression_compressed") == 1

# ---------------------------------------------------------------------------
# Test that compression does not re‑compress if limit unchanged
# ---------------------------------------------------------------------------

def test_no_recompression_if_limit_same():
    metrics = DummyMetrics()
    it = Iteration(iteration=5, tool_name="read_file", tool_call_result=large_text, model_response=None)
    history = [it]
    compress_history(metrics, history, upto=0)
    first_limit = it.compression_limit
    # Run again
    compress_history(metrics, history, upto=0)
    # No new counter
    assert sum(1 for msg in metrics.emitted if msg.get("name") == "compression_compressed") == 1
    assert it.compression_limit == first_limit
