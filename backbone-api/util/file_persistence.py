# inference-backbone/backbone-api/util/file_persistence.py
import json
from pathlib import Path

from contracts.inference_contracts.evidence import Evidence

# Base directory inside the container (mounted from host)
BASE_DIR = Path("/indexed-artifacts")

def _ensure_dir(p: Path) -> None:
    """Create the base directory if it does not exist."""
    p.mkdir(parents=True, exist_ok=True)

def write_evidence_to_file(evidence: Evidence, overwrite: bool = False) -> Path:
    """
    Persist the full Evidence payload as JSON.

    Parameters
    ----------
    evidence : Evidence
        The payload received from the ingest endpoint.
    overwrite : bool, default False
        If False and the file already exists, the function is a no‑op.

    Returns
    -------
    Path
        Absolute path to the written file.
    """
    store_path = BASE_DIR / "/evidence"
    _ensure_dir(store_path)
    
    file_path =  store_path / f"/{evidence.content_hash}.json"

    if file_path.exists() and not overwrite:
        # Idempotent: skip if already present
        return file_path

    # Serialize the Pydantic model to JSON (pretty‑printed for debugging)
    with file_path.open("w", encoding="utf-8") as fp:
        json.dump(evidence.model_dump(mode="json"), fp, indent=2, ensure_ascii=False)

    return file_path
