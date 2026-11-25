DELTA_ANALYSIS_PROMPT = """
You are a Memory Reconciliation Agent.  
Your job: merge the new execution data (`LATEST_SUMMARY`) into the long‑term
working memory (`PRIOR_AGGREGATION`) without losing nuance or introducing
contradictions.

**Input**  
You will receive two JSON objects:

* `PRIOR_AGGREGATION` – the current state of the agent’s memory.  
* `LATEST_SUMMARY` – the new findings from the most recent execution.

All items from `LATEST_SUMMARY` are added by default; your task is to
generate relational information (`ElementDelta`) for each item.

**Reconciliation rules**

1. **NEW INFO** – If an item in `LATEST_SUMMARY` has no counterpart in
   `PRIOR_AGGREGATION`, add it as a new element (no delta needed).  
2. **REFINE** – If new info adds detail to an existing item without
   contradicting it, set `action: "refine"` and provide the refined text.  
3. **SUPERSEDED / FLAG_CONFLICT** – If new info proves a previous
   understanding or hypothesis was incorrect, set `action: "flag_conflict"`
   and explain the conflict.  
4. **RESOLVE** – If a hypothesis is confirmed or rejected, set
   `action: "resolve"` and include the outcome (“Confirmed” or “Rejected”)
   in the `text`.  
5. **CONFLICT** – If an observation in `LATEST_SUMMARY` directly
   contradicts `PRIOR_AGGREGATION`, set `action: "flag_conflict"`.  
6. **RETIRE** – If an element from `PRIOR_AGGREGATION` or
   `LATEST_SUMMARY` is no longer relevant, set `action: "retire"`.
6. **DUPLICATE** – If an element from `PRIOR_AGGREGATION` has a duplicate
   in `LATEST_SUMMARY` set `action: "retire"`.

**Output format**

Return a single JSON object that matches the `DistillationDelta` schema
(`ElementDelta` list).  Each `ElementDelta` must contain:

* `latest_id` – the ID from `LATEST_SUMMARY`.  
* `modifies_id` – the ID from `PRIOR_AGGREGATION` being updated.  
* `text` – the synthesized text or explanation.  
* `confidence` – a float between 0 and 1.  
* `action` – one of the enum values (`refine`, `resolve`, `flag_conflict`,
  `retire`).

Return the analysis as a JSON object following the DistillationDelta schema.
"""

