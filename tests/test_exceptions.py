import pytest
from vellum.exceptions import DocumentNotFoundError, OptimisticLockError, VellumError


def test_document_not_found_is_vellum_error():
    err = DocumentNotFoundError("not found")
    assert isinstance(err, VellumError)
    assert str(err) == "not found"


def test_optimistic_lock_is_vellum_error():
    err = OptimisticLockError("version mismatch")
    assert isinstance(err, VellumError)
