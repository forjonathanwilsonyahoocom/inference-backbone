"""Edit a UTF‑8 text file by replacing a single exact occurrence of ``old_text`` with ``new_text``.

Parameters
----------
purpose : str
    Short description of why the edit is performed.
path : str
    Path to the target file, relative to the workspace root.
old_text : str
    Exact text to replace.
new_text : str
    Replacement string.

Returns
-------
str
    Status message indicating success or error.
"""