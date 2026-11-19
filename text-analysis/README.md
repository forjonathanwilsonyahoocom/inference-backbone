# Text Analysis Service

The **Text Analysis** service provides a set of NLP utilities that can be invoked via a FastAPI endpoint or used as a Docker‑based plugin. It is primarily used by the validator agent to generate summaries, sentiment scores, and term statistics for a set of documents.

## Endpoints

| Path | Method | Purpose |
|------|--------|---------|
| `/analyze` | POST | Run the full analysis pipeline on a list of files. |
| `/prep_report` | POST | Prepare a report that can be fed into the episode extractor. |
| `/health` | GET | Health‑check.

## Core pipeline

1. **File discovery** – `get_file_paths` collects all files with a given extension.
2. **Text loading** – `load_texts` reads the files into a list of dictionaries.
3. **Statistical analysis** – `compute_idf`, `compute_most_frequent_terms_and_entities`, and `compute_sentiment` produce IDF scores, frequent words/entities, and overall sentiment.
4. **Summarization** – `summarize_text` (via `textblob`/`sumy` or a custom algorithm) produces a short summary.
5. **Report construction** – `hacky_make_input_for_episode_extractor` turns the analysis into a `ReportForEpisodeExtraction` that the validator can consume.

## Docker plugin

The service can be run as a Docker plugin under `docker-broker/plugin_builds/text_analysis`. The plugin exposes the same endpoints and can be invoked via the broker’s `/on_demand` route.

## Example usage

```bash
curl -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"files": ["/data/report.txt"]}'
```

---

See the `contracts/general_contracts/text_analysis.py` contract for the exact request/response shape.
