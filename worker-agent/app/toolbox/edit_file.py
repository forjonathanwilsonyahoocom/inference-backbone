
from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE

@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    Edit a UTF-8 text file by replacing one exact occurrence of old_text
    with new_text.

    The file must already exist. The replacement is intentionally limited
    to one occurrence so the agent cannot accidentally modify multiple
    unrelated sections.
    """
    file_path = safe_path(path)

    if not file_path.exists():
        return f"File does not exist: {path}"

    if not file_path.is_file():
        return f"Not a file: {path}"

    content = file_path.read_text(encoding="utf-8")

    occurrences = content.count(old_text)

    if occurrences == 0:
        return (
            f"Could not edit {path}: old_text was not found. "
            "Read the file again and use an exact text match."
        )

    if occurrences > 1:
        return (
            f"Could not edit {path}: old_text occurs {occurrences} times. "
            "Provide a larger, more specific old_text block."
        )

    updated_content = content.replace(old_text, new_text, 1)
    file_path.write_text(updated_content, encoding="utf-8")

    return (
        f"Edited {file_path.relative_to(WORKSPACE)}: "
        f"replaced {len(old_text)} characters with {len(new_text)} characters."
    )


