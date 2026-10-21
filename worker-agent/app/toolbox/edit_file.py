
from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE

@tool
def edit_file(purpose: str, path: str, old_text: str, new_text: str) -> str:
    """Edit a UTF-8 text file by replacing old_text with new_text.

    Provide an exact old_text match and a precise new_text replacement.

    The file must already exist. The replacement is intentionally limited
    to one occurrence so we cannot accidentally modify multiple
    unrelated sections.

    Parameters
    ----------
    purpose : str
        The immediate purpose of this call.
    path : str
        Path to the file to edit (relative to the workspace root).
        The path is resolved through ``safe_path`` which validates it is within the workspace.
    old_text : str
        The exact text to find and replace. Must be an exact substring match.
    new_text : str
        The replacement text.

    Returns
    -------
    str
        A status message indicating success, or an error if the file
        does not exist, old_text was not found, or multiple occurrences
        were detected.

    Notes
    -----
    * If ``old_text`` appears more than once in the file, the tool returns
      an error to prevent unintended modifications.
    * The file is read with UTF-8 encoding; if decoding fails, ``latin-1``
      is used as a fallback.
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


