# Worker Agent

The **Worker Agent** is the runtime that executes LLM‑driven agent runs. It exposes two FastAPI endpoints:

* **POST `/run`** – accepts an `AgentRequest` payload, builds a toolchain, and runs the agent loop. The request can specify either `worker_tools` or `knowledge_tools` mode.
* **GET `/health`** – simple health‑check.

## Core responsibilities

| Responsibility | How it is implemented |
|----------------|-----------------------|
| **LLM orchestration** | Two `ChatOllama` instances are created – one for the main agent and one for distillation. The main LLM is bound with a set of tools (search, file I/O, Docker, etc.) via LangChain’s `bind_tools`.
| **Toolchain construction** | `get_toolchain` builds a dictionary of tool names to tool objects. The tools include:   * `analyze_workspace`, `list_files`, `read_file`, `write_file`, `edit_file`, `search_file`, `search_history`, `run_command`, `web_search`, `web_fetch`, `run_in_workspace`.   * `assess_result` and `search_history` wrappers curry needed  system context to tool calls.
| **Metrics** | A global `MetricsWrapper` is initialised on startup and passed to the agent loop. Prometheus metrics are exposed on port 8080.
| **Distillation** | The agent’s final output is passed to a second LLM (`distill_llm`) with structured output (`AgentState`).

## Key modules

* `app/main.py` – FastAPI app and endpoint definitions.
* `app/agent/loop.py` – the main agent execution loop.
* `app/agent/models.py` – data models for requests and iterations.
* `app/toolbox/` – a collection of LangChain tools used by the agent.

## Usage example

```bash
curl -X POST http://localhost:8000/run \
  -H 'Content-Type: application/json' \
  -d '{
        "mode": "worker_tools",
        "worker_model": "llama3.1",
        "worker_temp": 0.1,
        "worker_num_ctx": 8192,
        "distillation_model": "gpt-oss:20b",
        "distillation_temp": 0.1,
        "distillation_num_ctx": 8192,
        "base_url": "http://localhost:11434"
      }'
```

The response contains the agent’s structured state and any metrics.

---

For more details, see the [AGENTS.md](../AGENTS.md) documentation.
