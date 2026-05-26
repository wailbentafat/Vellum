from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from pydantic import PlainSerializer
from pydantic.functional_validators import BeforeValidator


def _coerce_uuid(v: Any) -> UUID:
    if isinstance(v, UUID):
        return v
    if isinstance(v, str):
        return UUID(v)
    raise ValueError(f"Cannot coerce {type(v).__name__} to UUID")


Reference = Annotated[
    UUID,
    BeforeValidator(_coerce_uuid),
    PlainSerializer(lambda u: str(u), return_type=str, when_used="always"),
]

__all__ = ["Reference"]
