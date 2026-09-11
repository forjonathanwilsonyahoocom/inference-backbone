"""Utility for deterministic text chunking.

The chunker splits a string into overlapping chunks of a maximum
character length.  The algorithm is intentionally simple and
deterministic so that repeated ingestion of the same content yields
identical chunk boundaries.

The public API is a single function:

```
chunk_text(content: str, max_size: int = 4000, overlap: int = 400) -> List[str]
```

It returns a list of chunks in order.  The caller is responsible for
calculating indices and counts.
"""

from __future__ import annotations

from typing import List


def chunk_text(content: str, max_size: int = 4000, overlap: int = 400) -> List[str]:
    """Split *content* into overlapping chunks.

    Parameters
    ----------
    content:
        The raw text to split.
    max_size:
        Maximum number of characters per chunk.
    overlap:
        Number of characters that overlap between consecutive chunks.

    Returns
    -------
    List[str]
        Ordered list of chunks.
    """
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non‑negative")
    if overlap >= max_size:
        raise ValueError("overlap must be smaller than max_size")

    chunks: List[str] = []
    start = 0
    content_len = len(content)
    while start < content_len:
        end = min(start + max_size, content_len)
        chunks.append(content[start:end])
        if end == content_len:
            break
        start = end - overlap
    return chunks

# End of module
