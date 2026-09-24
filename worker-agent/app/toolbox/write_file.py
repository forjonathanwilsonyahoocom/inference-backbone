
from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE_PATH
from typing import Any

@tool
def write_file(path: str, content: Any, overwrite: bool = False) -> str:
    """
    Write `content` to `path`.  
    - If the file exists and `overwrite` is False (default), the call is a no‑op
      and you get a short “file exists” message.
    - If `overwrite` is True, the existing file is simply replaced.
    - `content` may be:
        • a mapping → pretty‑printed JSON (unless it contains a single string)
        • a string → written verbatim (real newlines, no `\\n`)

    Returns a human‑readable status message.
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

