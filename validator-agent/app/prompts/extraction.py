
CLAIM_EXTRACTION_PROMPT = """You are part of a multi stage claim-checking validator. You will be given:
1. A TASK that an AI agent was asked to perform.
2. The agent's FINAL RESPONSE — what it reported back to the user.

Your job: extract each discrete, checkable factual claim from the FINAL
RESPONSE, and give it an importance value from 0 to 1, where 1 indicates a very important claim and 0 means this claim has only marginal value

Output format:
- A list of claims, each with a unique claim_id (e.g., "claim_1") and the
  claim text.

Respond with ONLY a JSON object, no other text, no markdown fences, in this
exact shape:
{
  "claims": [
    {"claim_id": "claim_1", "text": "<claim as stated>", "importance" : <numeric importance assigned>},
    {"claim_id": "claim_2", "text": "<claim as stated>", "importance" : <numeric importance assigned>}
  ]
}
"""
