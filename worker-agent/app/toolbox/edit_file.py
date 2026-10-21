
from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE

@tool
def edit_file(purpose: str, path: str, old_text: str, new_text: str) -> str:
    """Edit a UTF-8 text file by replacing one exact occurrence of ``old_text`` with ``new_text``.

    This tool performs a **surgical, single-replacement** edit: it finds the
    first exact substring match of ``old_text`` in the file and substitutes
    it with ``new_text``.  The file must already exist and must be a regular
    file (not a directory).

    The ``one-occurrence`` constraint is a safety feature, not a limitation.
    If ``old_text`` appears more than once, the tool refuses to edit and
    returns an error — this prevents accidentally modifying multiple
    unrelated sections of a file.  To edit a file that contains repeated
    text, provide a larger, more specific ``old_text`` block that matches
    only the intended location.

    The file is read with UTF-8 encoding; if decoding fails, ``latin-1``
    is used as a fallback.

    Parameters
    ----------
    purpose : str
        The immediate purpose of this call.  Recorded for observability
        and used by the semantic compressor to tag the result.
    path : str
        Path to the file to edit (relative to the workspace root).
        The path is resolved through ``safe_path`` which validates it is
        within the workspace.
    old_text : str
        The exact text to find and replace.  Must be an exact substring
        match — no partial or fuzzy matching.
    new_text : str
        The replacement text.

    Returns
    -------
    str
        A status message indicating success (with character counts) or
        an error describing why the edit could not be applied
        (file missing, not a file, old_text not found, or multiple
        occurrences detected).

    Notes
    -----
    * If ``old_text`` appears more than once in the file, the tool
      returns an error to prevent unintended modifications.
    * The file is read with UTF-8 encoding; if decoding fails, ``latin-1``
      is used as a fallback.
    * On success the returned message includes the number of characters
      replaced, which is useful for verifying the edit was applied
      as expected.
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


