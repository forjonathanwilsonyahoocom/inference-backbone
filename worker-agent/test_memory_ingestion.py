import os
import uuid
import json
import pytest

# Set environment variables required by main
os.environ['OLLAMA_BASE_URL'] = 'http://10.42.0.192:11434/'
os.environ['GEN_MODEL'] = 'gpt-oss:20b'

# Import the module after setting env
from inference_backbone.worker_agent import main as worker_main

# Patch uuid.uuid4 to deterministic values
original_uuid4 = uuid.uuid4

def deterministic_uuid4():
    return uuid.UUID('11111111-1111-1111-1111-111111111111')

# Patch requests.post to capture calls
import requests
captured = []

def fake_post(url, json=None, timeout=None):
    captured.append({'url': url, 'json': json, 'timeout': timeout})
    class DummyResp:
        def raise_for_status(self):
            pass
    return DummyResp()

# Patch llm_with_tools.invoke
class DummyResponse:
    def __init__(self, tool_calls, content=""):
        self.tool_calls = tool_calls
        self.content = content
        self.usage_metadata = {"input_tokens": 0}

# Apply patches
uuid.uuid4 = deterministic_uuid4
requests.post = fake_post

# Patch llm_with_tools.invoke
worker_main.llm_with_tools.invoke = lambda *args, **kwargs: DummyResponse(
    tool_calls=[{"name": "read_file", "args": {"path": "README.md"}, "id": "1"}]
)

# Run the agent with a simple request
result = worker_main.run_agent("Please read the README.md file.")

# Assertions
assert result["condition"] != "no tool calls", "Agent did not perform any tool calls"
assert len(captured) == 1, "Memory ingestion was not called"
payload = captured[0]["json"]
assert payload["artifact_type"] == "tool_result"
assert payload["execution_id"] == "11111111-1111-1111-1111-111111111111"
assert payload["event_id"] == "11111111-1111-1111-1111-111111111111"
assert payload["source"] == "read_file"
assert payload["source_url"] is None
assert "content" in payload

# Clean up patches
uuid.uuid4 = original_uuid4
requests.post = requests.sessions.Session.post

print("Test passed.")
