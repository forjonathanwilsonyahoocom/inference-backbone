from typing import Any
import json
import hashlib

def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    

def tool_call_fingerprint(tool_name: str, args: dict) -> str:
    payload = {
        "tool": tool_name,
        "args": args,
    }

    encoded = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
    
def result_fingerprint(result: Any) -> str:
    encoded = canonical_json(result).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


