from uuid import uuid4

import pytest
import pytest_asyncio

from vellum.exceptions import DocumentNotFoundError
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


class Product(VellumBaseModel):
    name: str
    price: float

    class Settings:
        collection_name = "products"
        indexes = [
            {"key": [("name", 1)], "unique": True},
        ]


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(Product, db)


@pytest.mark.asyncio
async def test_create_and_get(repo):
    product = Product(name="Widget", price=9.99)
    created = await repo.create(product)
    fetched = await repo.get(created.id)
    assert fetched.name == "Widget"
    assert fetched.price == 9.99


@pytest.mark.asyncio
async def test_get_not_found_raises(repo):
    with pytest.raises(DocumentNotFoundError):
        await repo.get(uuid4())


@pytest.mark.asyncio
async def test_update(repo):
    product = Product(name="Gadget", price=19.99)
    await repo.create(product)
    product.price = 24.99
    updated = await repo.update(product.id, product)
    assert updated.price == 24.99
    fetched = await repo.get(product.id)
    assert fetched.price == 24.99


@pytest.mark.asyncio
async def test_delete(repo):
    product = Product(name="Doohickey", price=5.00)
    await repo.create(product)
    result = await repo.delete(product.id)
    assert result is True
    with pytest.raises(DocumentNotFoundError):
        await repo.get(product.id)


@pytest.mark.asyncio
async def test_delete_not_found_raises(repo):
    with pytest.raises(DocumentNotFoundError):
        await repo.delete(uuid4())


@pytest.mark.asyncio
async def test_find_all(repo):
    await repo.create(Product(name="A", price=1.0))
    await repo.create(Product(name="B", price=2.0))
    results = await repo.find()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_find_with_filter(repo):
    await repo.create(Product(name="Cheap", price=1.0))
    await repo.create(Product(name="Expensive", price=100.0))
    results = await repo.find({"name": "Cheap"})
    assert len(results) == 1
    assert results[0].name == "Cheap"


@pytest.mark.asyncio
async def test_count(repo):
    await repo.create(Product(name="X", price=1.0))
    await repo.create(Product(name="Y", price=2.0))
    total = await repo.count()
    assert total == 2
    filtered = await repo.count({"name": "X"})
    assert filtered == 1


@pytest.mark.asyncio
async def test_ensure_indexes(repo):
    await repo.ensure_indexes()
    await repo.create(Product(name="Unique", price=1.0))
    with pytest.raises(Exception):
        await repo.create(Product(name="Unique", price=2.0))
