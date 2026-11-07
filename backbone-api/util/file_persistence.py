# inference-backbone/backbone-api/util/file_persistence.py

from pathlib import Path

from pydantic import BaseModel


# Base directory inside the container, mounted from the host
BASE_DIR = Path("/indexed-artifacts")


def _ensure_dir(path: Path) -> None:
    """Create a directory and its parents if they do not exist."""
    path.mkdir(parents=True, exist_ok=True)


def write_to_file(
    content: BaseModel | str,
    location: str,
    identifier: str,
    overwrite: bool = False,
) -> Path:
    """
    Persist any Pydantic model as JSON.

    Parameters
    ----------
    content:
        Any Pydantic BaseModel instance or a string.
    location:
        Relative subdirectory under BASE_DIR.
    identifier:
        Filename without the .json extension.
    overwrite:
        If False and the file already exists, do nothing.

    Returns
    -------
    Path
        Absolute path to the persisted file.
    """
    store_path = BASE_DIR / location
    _ensure_dir(store_path)

    file_path = store_path / f"{identifier}.json"

    if file_path.exists() and not overwrite:
        return file_path

    persist_this = content
    if isinstance(BaseModel, content):
        persist_this = content.model_dump_json(
            indent=2,
            ensure_ascii=False,
        )

    file_path.write_text(
        persist_this,
        encoding="utf-8",
    )

    return file_path

