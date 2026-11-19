# Validator Agent

The **Validator Agent** is responsible for extracting claims from an agent’s final answer, validating those claims against evidence, and assembling an episode that captures the entire reasoning trace.

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/extract_claims` | POST | Extract discrete, checkable claims from the final answer of a run. |
| `/validate` | POST | Rate each claim against evidence items and produce a support map. |
| `/make_episode` | POST | Build an episode from the full trace of a run and persist it to GraphDB/Weaviate. |
| `/make_episode_from_report` | POST | Build an episode directly from a pre‑generated report. |
| `/health` | GET | Health‑check. |

## Workflow

1. **Claim extraction** – The agent’s task and final answer are fetched via the telemetry helpers. The LLM (configured via `get_ollama_config`) is invoked with the `CLAIM_EXTRACTION_PROMPT` to produce a list of `Claim` objects.
2. **Validation** – For each claim, the LLM is called with the `VALIDATION_PROMPT` and the evidence items retrieved by `fetch_events("claim", ...)`. The result is a `ValidationResult` containing a support map.
3. **Episode assembly** – The full trace is collected, a `ReportForEpisodeExtraction` is built, and the episode is extracted using the `Episode` contract. The episode is then ingested into the knowledge graph.

## Key modules

* `app/main.py` – FastAPI app and endpoint definitions.
* `app/agent/telemetry.py` – Helpers for fetching events and assembling reports.
* `app/agent/episode.py` – Extracts an episode from a report.
* `app/agent/loop.py` – Handles claim extraction and validation logic.

## Example usage

```bash
# Extract claims
curl -X POST http://localhost:8000/extract_claims \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": "run-123"}'

# Validate claims
curl -X POST http://localhost:8000/validate \
  -H 'Content-Type: application/json' \
  -d '{"execution_id": "run-123"}'
```

---

See the [AGENTS.md](../AGENTS.md) for a deeper dive.
