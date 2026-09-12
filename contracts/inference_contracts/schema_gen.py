import json
from pathlib import Path

from inference_contracts.evidence import Evidence

# Helper to generate JSON Schema for the Evidence model.
# This is used by the validator and tests.

def evidence_schema() -> dict:
    return Evidence.model_json_schema()

# Persist the schema to a file for external consumption.

def write_schema(path: str | Path = "inference-backbone/contracts/inference_contracts/evidence_schema.json") -> None:
    Path(path).write_text(json.dumps(evidence_schema(), indent=2))

if __name__ == "__main__":
    write_schema()
    print("Evidence schema written to inference_contracts/evidence_schema.json")
