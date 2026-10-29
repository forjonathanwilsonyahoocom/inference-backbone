
EPISODE_PROMPT = """You are part of a multi stage memory building pipeline. You will be given:

1. A high level summary of an agents execution of a task

Your job: 
- Reconstruct the agent's experience, not merely the subject matter it investigated.
- Determine the outcome of the original mission using the available evidence.
- Distinguish observed events from inferred explanations.
- Do not assume that a successful tool call means the overall mission succeeded.
- Do not assume that the agent's final response accurately describes what happened.
- Include findings only when they may be useful beyond the immediate execution.
- Do not invent lessons, causes, or evidence references.
- Use `unknown` when the mission outcome cannot be determined reliably.

Respond with ONLY a JSON object, no other text, no markdown fences
"""


