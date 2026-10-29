#!/usr/bin/env python3
"""
Text Analysis Tool
===================
this just wraps the tat in a fastapi
"""
from fastapi import FastAPI
from pathlib import Path
import os
from contracts.general_contracts.text_analysis import TextAnalysis, TargetFileList
from analyzer import analyze, hacky_make_input_for_episode_extractor

WORKSPACE_PATH = os.getenv(
    "WORKSPACE",
    "/srv/corpus",
)
WORKSPACE = Path(WORKSPACE_PATH)

WORKSPACE.mkdir(parents=True, exist_ok=True)

WORKSPACE = WORKSPACE.resolve()
print(WORKSPACE)

def get_file_paths(workdir: Path, files: list[str] | None, ext: str) -> list[Path]:
    """Return a list of file paths to analyze.

    If ``file`` is provided, it is resolved relative to ``workdir`` and
    returned as a single‑item list.  Otherwise all files matching ``ext``
    under ``workdir`` (recursively) are returned.
    """
    
    if files:
        paths=[]
        for file in files:
            target = workdir / file
            if not target.is_file():
                raise FileNotFoundError(f"Specified file not found: {target}")
            paths.append(target)
        return paths
    # No specific file – find all matching files
    return sorted(workdir.rglob(ext))

        
            
app = FastAPI()

@app.post("/analyze")
async def run_analyzer(on_files: TargetFileList):
    to_analyze = get_file_paths(WORKSPACE, on_files.files, None)
    result = analyze(WORKSPACE, to_analyze)
    return result


@app.post("/prep_report")
async def run_analyzer(on_files: TargetFileList):
    to_analyze = get_file_paths(WORKSPACE, on_files.files, None)
    result = analyze(WORKSPACE, to_analyze)
    report = hacky_make_input_for_episode_extractor(result)
    return report


@app.get("/health")
def health():
    return {"status": "ok"}

