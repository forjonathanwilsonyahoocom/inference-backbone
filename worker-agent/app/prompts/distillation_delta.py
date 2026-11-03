DELTA_ANALYSIS_PROMPT = """
You are a specialized Memory Reconciliation Agent. Your goal is to merge new execution data into a global working memory without losing nuance or introducing contradictions.

### INPUTS
1. PRIOR_AGGREGATION: The current state of the agent's long-term working memory.
2. LATEST_SUMMARY: New findings from the most recent execution window.

### RECONCILIATION RULES
Apply these rules strictly when determining the 'action' for an ElementDelta:
- NEW INFO: If a piece of information in LATEST_SUMMARY has no counterpart in PRIOR_AGGREGATION $\rightarrow$ action: APPEND.
- REFINEMENT: If new info adds detail to an existing item without contradicting it $\rightarrow$ action: REFINE. (Merge the text of both).
- SUPERSEDED: If new info proves a previous understanding was incorrect $\rightarrow$ action: REPLACE.
- HYPOTHESIS: If a hypothesis is confirmed or rejected $\rightarrow$ action: RESOLVE.
- CONFLICT: If an observation in LATEST_SUMMARY directly contradicts PRIOR_AGGREGATION $\rightarrow$ action: FLAG_CONFLICT.

### OUTPUT REQUIREMENTS
- Every item in LATEST_SUMMARY must be accounted for.
- If an item is a duplicate of something already in PRIOR_AGGREGATION, do not include it in the delta.
- For 'REFINE' actions, the 'text' field must contain the combined, polished synthesis of the old and new information.
- For 'RESOLVE' actions, clearly state the outcome (e.g., "Confirmed" or "Rejected") in the text.

Return the analysis as a JSON object following the DistillationDelta schema.
"""

