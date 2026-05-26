import pytest

from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


class ValidatedItem(VellumBaseModel):
    name: str
    price: float

    class Settings:
        collection_name = "validated_items"


@pytest.mark.asyncio
async def test_valid_document_passes_validation(db):
    repo = VellumRepository(ValidatedItem, db)
    await repo.set_schema_validation()
    item = ValidatedItem(name="Valid", price=10.0)
    created = await repo.create(item)
    assert created.name == "Valid"


@pytest.mark.asyncio
async def test_invalid_document_is_rejected(db):
    repo = VellumRepository(ValidatedItem, db)
    await repo.set_schema_validation()
    with pytest.raises(Exception):
        await repo.collection.insert_one({"name": "Bad", "price": "not-a-number"})


@pytest.mark.asyncio
async def test_missing_required_field_is_rejected(db):
    repo = VellumRepository(ValidatedItem, db)
    await repo.set_schema_validation()
    with pytest.raises(Exception):
        await repo.collection.insert_one({"name": "NoPrice"})


@pytest.mark.asyncio
async def test_schema_can_be_set_multiple_times(db):
    repo = VellumRepository(ValidatedItem, db)
    await repo.set_schema_validation()
    await repo.set_schema_validation()
    item = ValidatedItem(name="Durable", price=5.0)
    created = await repo.create(item)
    assert created.name == "Durable"
