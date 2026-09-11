# inference_contracts/__init__.py
"""Package for shared inference contracts.

This module exposes the :class:`Evidence` data model which is generated
from the JSON‑Schema located at ``contracts/evidence/v1/schema.json``.

The model is defined using :class:`pydantic.BaseModel` so that it can be
used both as a runtime type and for validation in tests and services.
"""

from .evidence import Evidence

__all__ = ["Evidence"]

