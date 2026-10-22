import json
from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE_PATH
from typing import Any, Mapping

@tool
def write_file(about: str, path: str, content: Any, overwrite: bool = False) -> str:
    """Write content to a file.

    Parameters
    ----------
    about : str
        A short description of what the call is about, hint for summarization and retrieval.
    path : str
        Relative file path within the workspace. path is created as required.
    content : Any
        Data to write; mapping is JSON, string is raw.
    overwrite : bool, optional
        If True, replace existing file; otherwise no‑op if file exists.

    Returns
    -------
    str
        Status message indicating success or that the file already exists.
    """

    file_path = safe_path(path)

    if isinstance(content, Mapping):
        if "content" in content and isinstance(content["content"], str):
            content_str = content["content"]
        else:
            content_str = json.dumps(content, indent=2, ensure_ascii=False)
    elif isinstance(content, str):
        content_str = content
    else:
        raise TypeError(f"Unsupported content type {type(content)}")

    if file_path.exists() and not overwrite:
        return (
            f"File already exists: {path}. "
            "Use `overwrite=True` to replace it or use `read_file` + "
            "`edit_file` to modify it."
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content_str, encoding="utf-8")
    return (
        f"Created {len(content_str)} characters in "
        f"{file_path.relative_to(WORKSPACE_PATH)}"
    )

