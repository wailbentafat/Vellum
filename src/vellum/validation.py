from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_PATTERN = re.compile(
    r"^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[-\w$.+!*\'(),;:@&=?/~#%]*)?$"
)


class ValidationMixin:

    @staticmethod
    def validate_email(value: str) -> str:
        if not EMAIL_PATTERN.match(value):
            raise ValueError(f"Invalid email: {value}")
        return value

    @staticmethod
    def validate_url(value: str) -> str:
        if not URL_PATTERN.match(value):
            raise ValueError(f"Invalid URL: {value}")
        return value

    @staticmethod
    def validate_length(value: str, min_len: int = 0, max_len: int | None = None) -> str:
        if len(value) < min_len:
            raise ValueError(f"Length must be >= {min_len}, got {len(value)}")
        if max_len is not None and len(value) > max_len:
            raise ValueError(f"Length must be <= {max_len}, got {len(value)}")
        return value

    @staticmethod
    def validate_gt(value: float | int, threshold: float | int) -> float | int:
        if not (value > threshold):
            raise ValueError(f"Value must be > {threshold}, got {value}")
        return value

    @staticmethod
    def validate_ge(value: float | int, threshold: float | int) -> float | int:
        if not (value >= threshold):
            raise ValueError(f"Value must be >= {threshold}, got {value}")
        return value

    @staticmethod
    def validate_lt(value: float | int, threshold: float | int) -> float | int:
        if not (value < threshold):
            raise ValueError(f"Value must be < {threshold}, got {value}")
        return value

    @staticmethod
    def validate_le(value: float | int, threshold: float | int) -> float | int:
        if not (value <= threshold):
            raise ValueError(f"Value must be <= {threshold}, got {value}")
        return value
