from pydantic import BaseModel
from typing import List, Dict, Tuple

class TextAnalysis(BaseModel):
    idf_top: List[Tuple[str, float]]
    frequent_words: List[Tuple[str, int]]
    overall_gist: str | None = None
    overall_sentiment: float | None = None
    summary: List[Dict]
    
class TargetFileList(BaseModel):
    files: List[str]


