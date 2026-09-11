import os
import pytest
import json
from inference_backbone.fastapi.embedding_provider import OllamaEmbeddingProvider

# Helper to create a mock httpx transport
from httpx import Response, Request

async def mock_response(request: Request, *args, **kwargs):
    # Return a simple embedding response based on input
    payload = request.json()
    model = payload.get("model")
    input_data = payload.get("input")
    if isinstance(input_data, list):
        embeddings = [[0.1 * i for i in range(10)] for _ in input_data]
    else:
        embeddings = [[0.1 * i for i in range(10)]]
    return Response(200, json={"embeddings": embeddings})

@pytest.fixture
def provider(monkeypatch):
    # Set required env var
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://mockserver:11434")
    # Use default model
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "test-model")
    # Patch httpx.AsyncClient to use mock transport
    from httpx import AsyncClient, AsyncMockTransport
    transport = AsyncMockTransport(mock_response)
    monkeypatch.setattr(AsyncClient, "__init__", lambda self, base_url=None, transport=None: setattr(self, "transport", transport))
    return OllamaEmbeddingProvider()

@pytest.mark.asyncio
async def test_embed_documents(provider):
    texts = ["hello", "world"]
    embeddings = await provider.embed_documents(texts)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert all(isinstance(e, list) for e in embeddings)
    assert all(len(e) == 10 for e in embeddings)

@pytest.mark.asyncio
async def test_embed_query(provider):
    text = "single"
    embedding = await provider.embed_query(text)
    assert isinstance(embedding, list)
    assert len(embedding) == 10

@pytest.mark.asyncio
async def test_missing_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    with pytest.raises(ValueError):
        OllamaEmbeddingProvider()

# End of tests
