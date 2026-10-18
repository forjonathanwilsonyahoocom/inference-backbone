import json
import pytest
from agent.compression import compress_history
from agent.models import AgentRequest, Iteration

class DummyMetrics:
    def __init__(self):
        self.emitted = []
    def emit(self, msg):
        self.emitted.append(msg)

@pytest.fixture
def config():
    return AgentRequest(compression_tiers=[(1, 2000)])

@pytest.fixture
def metrics():
    return DummyMetrics()

@pytest.fixture
def history():
    it = Iteration(
        iteration=1,
        tool_name="search_evidence",
        tool_call_result="raw result",
        tool_call_result_instance_number=42,
        tool_call_args={"purpose": "find foo"},
        execution_id="exec-1"
    )
    return [it]

def test_success(monkeypatch, config, metrics, history):
    # mock search_evidence to return 3 chunks
    def fake_search_evidence(purpose, query, limit=8, instance_number=None, execution_id=None):
        chunks = [
            {"text": "chunk1", "distance": 0},
            {"text": "chunk2", "distance": 1},
            {"text": "chunk3", "distance": 2}
        ]
        return json.dumps(chunks)
    monkeypatch.setattr(compression, "search_evidence", fake_search_evidence)

    compression.compress_history(config, metrics, history, upto=0)
    it = history[0]
    assert it.tool_call_result_chunks is not None
    assert len(it.tool_call_result_chunks) == 3
    # compressed string should be concatenated chunks
    assert it.tool_call_result_compressed == "chunk1\nchunk2\nchunk3"

def test_empty_result(monkeypatch, config, metrics, history):
    def fake_search_evidence(*_, **__):
        return json.dumps([])
    monkeypatch.setattr(compression, "search_evidence", fake_search_evidence)
    compression.compress_history(config, metrics, history, upto=0)
    it = history[0]
    assert it.tool_call_result_chunks == []
    assert it.tool_call_result_compressed == ""

def test_error(monkeypatch, config, metrics, history):
    def fake_search_evidence(*_, **__):
        raise RuntimeError("boom")
    monkeypatch.setattr(compression, "search_evidence", fake_search_evidence)
    compression.compress_history(config, metrics, history, upto=0)
    it = history[0]
    # chunks remain None
    assert it.tool_call_result_chunks is None
    # compressed result unchanged (original raw)
    assert it.tool_call_result_compressed is None
    # metrics should have recorded error
    assert any(m.get("name") == "compression_error" for m in metrics.emitted)
