class VellumError(Exception):
    """Base exception for all Vellum errors."""


class DocumentNotFoundError(VellumError):
    """Raised when a requested document does not exist in the collection."""


class OptimisticLockError(VellumError):
    """Raised when an update fails due to a version mismatch (concurrent modification)."""


class HookError(VellumError):
    """Raised when a lifecycle hook raises an exception."""
