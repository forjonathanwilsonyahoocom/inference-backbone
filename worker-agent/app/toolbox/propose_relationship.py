import json

from langchain.tools import tool
from typing import  Any
import json



@tool
def propose_relationship(about: str, 
                         source_chunk_id: str,
                         target_chunk_id: str,
                         relationship_type: str,
                         explanation: str,
                         confidence: float) -> str:
    """record a proposed relationship between candidate chunks

Parameters
----------
about : str
    A short description of what the call is about, hint for summarization and retrieval.
source_chunk_id : str
    the first chunk in the relationship
target_chunk_id : str
    the second chunk in the relationship
relationship_type : str
    relationship_type is one of:
    {"related_to",
     "supports",
     "contradicts",
     "refines",
     "generalizes",
     "specializes"}
     
explanation : str
    short summary of relationship 
confidence : float 
    0.0 to 1.0 assessment of certainty

Returns
-------
str
    JSON‑encoded representation of relationship.
    
"""
    payload = {
        "source_chunk_id": source_chunk_id,
        "target_chunk_id": target_chunk_id,
        "relationship_type": relationship_type,
        "explanation": explanation,
        "confidence": confidence,
    }
   
    return json.dumps(payload, ensure_ascii=False, indent=2)
        

def compress_propose_relationship(result: Any, limit: int) -> str:
    """Return unmodified."""
    
    return result
