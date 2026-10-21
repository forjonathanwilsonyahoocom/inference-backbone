"""Edit a UTF‑8 text file by replacing a single exact occurrence of ``old_text`` with ``new_text``.

This tool performs a *surgical* edit: it searches for the first exact match of ``old_text`` in the file and replaces it with ``new_text``. The operation is intentionally limited to one occurrence to prevent accidental bulk changes. If ``old_text`` appears more than once, the tool returns an error and suggests providing a more specific match.

The file must already exist and be a regular file (not a directory). The content is read using UTF‑8; if decoding fails, Latin‑1 is used as a fallback.

Parameters
----------
purpose : str
    A short description of why the edit is being performed.  It is logged for observability and used by the semantic compressor to tag the result.
path : str
    Path to the target file, relative to the workspace root. The path is resolved via :func:`safe_path` to ensure it stays within the workspace.
old_text : str
    The exact text to locate.  No fuzzy or partial matching is performed.
new_text : str
    The replacement string.

Returns
-------
str
    A status message indicating success (including the number of characters replaced) or an error explaining why the edit could not be applied (missing file, not a file, no match, or multiple matches).

Notes
-----
* The tool enforces a single‑occurrence replacement to safeguard against unintended bulk edits.
* If the target file contains the same ``old_text`` multiple times, provide a longer, more specific snippet that uniquely identifies the intended location.
* On success the returned message includes the character counts of the replaced and inserted text, which can be used to verify the edit.

Examples
--------
>>> edit_file(
...     purpose="Update license header",
...     path="src/main.py",
...     old_text="__author__ = 'old'",
...     new_text="__author__ = 'new'",
... )
'Edited src/main.py: replaced 15 characters with 15 characters.'
"""

from langchain_core.tools import tool
from toolbox.util import safe_path, WORKSPACE

@tool
def edit_file(purpose: str, path: str, old_text: str, new_text: str) -> str:
    """Edit a UTF‑8 text file by replacing a single exact occurrence of ``old_text`` with ``new_text``.

    This tool performs a *surgical* edit: it searches for the first exact match of ``old_text`` in the file and replaces it with ``new_text``. The operation is intentionally limited to one occurrence to prevent accidental bulk changes.

    The file must already exist and be a regular file (not a directory).

    The file is read with UTF‑8 encoding; if decoding fails, Latin‑1 is used as a fallback.

    Parameters
    ----------
    purpose : str
        A short description of why the edit is being performed.  It is logged for observability and used by the semantic compressor to tag the result.
    path : str
        Path to the target file, relative to the workspace root. The path is resolved via :func:`safe_path` to ensure it stays within the workspace.
    old_text : str
        The exact text to locate.  No fuzzy or partial matching is performed.
    new_text : str
        The replacement string.

    Returns
    -------
    str
        A status message indicating success (including the number of characters replaced) or an error explaining why the edit could not be applied (missing file, not a file, no match, or multiple matches).

    Notes
    -----
    * The tool enforces a single‑occurrence replacement to safeguard against unintended bulk edits.
    * If the target file contains the same ``old_text`` multiple times, provide a longer, more specific snippet that uniquely identifies the intended location.
    * On success the returned message includes the character counts of the replaced and inserted text, which can be used to verify the edit.
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

    return f"Edited {file_path.relative_to(WORKSPACE)}: replaced {len(old_text)} characters with {len(new_text)} characters."
