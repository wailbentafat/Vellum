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


@pytest.mark.asyncio
async def test_find_one_returns_none_when_not_found(repo):
    result = await repo.find_one({"name": "Nope"})
    assert result is None


@pytest.mark.asyncio
async def test_find_one_returns_document(repo):
    await repo.create(Product(name="Match", price=1.0))
    result = await repo.find_one({"name": "Match"})
    assert result is not None
    assert result.name == "Match"


@pytest.mark.asyncio
async def test_find_one_with_sort(repo):
    await repo.create(Product(name="B", price=2.0))
    await repo.create(Product(name="A", price=1.0))
    result = await repo.find_one(sort=[("name", 1)])
    assert result is not None
    assert result.name == "A"


@pytest.mark.asyncio
async def test_find_or_create_returns_existing(repo):
    await repo.create(Product(name="Existing", price=5.0))
    result = await repo.find_or_create({"name": "Existing"})
    assert result.name == "Existing"
    assert result.price == 5.0


@pytest.mark.asyncio
async def test_find_or_create_creates_new(repo):
    result = await repo.find_or_create({"name": "New"}, defaults={"price": 10.0})
    assert result.name == "New"
    assert result.price == 10.0
    count = await repo.count({"name": "New"})
    assert count == 1


@pytest.mark.asyncio
async def test_upsert_inserts_new_document(repo):
    p = Product(name="Fresh", price=3.0)
    result = await repo.upsert({"name": "Fresh"}, p)
    assert result.name == "Fresh"
    fetched = await repo.get(result.id)
    assert fetched.price == 3.0


@pytest.mark.asyncio
async def test_upsert_replaces_existing(repo):
    original = Product(name="ReplaceMe", price=1.0)
    await repo.create(original)
    replacement = Product(name="ReplaceMe", price=99.0)
    await repo.upsert({"name": "ReplaceMe"}, replacement)
    updated = await repo.get(original.id)
    assert updated.price == 99.0


@pytest.mark.asyncio
async def test_bulk_create_inserts_all(repo):
    products = [Product(name=f"Bulk{i}", price=float(i)) for i in range(3)]
    created = await repo.bulk_create(products)
    assert len(created) == 3
    count = await repo.count()
    assert count >= 3


@pytest.mark.asyncio
async def test_bulk_update_modifies_all(repo):
    items = [Product(name=f"U{i}", price=1.0) for i in range(3)]
    await repo.bulk_create(items)
    for item in items:
        item.price = 99.0
    updated = await repo.bulk_update(items)
    assert all(u.price == 99.0 for u in updated)
    all_items = await repo.find()
    for item in all_items:
        assert item.price == 99.0


@pytest.mark.asyncio
async def test_bulk_delete_removes_matching(repo):
    items = [Product(name=f"D{i}", price=1.0) for i in range(3)]
    await repo.bulk_create(items)
    filters = [{"name": f"D{i}"} for i in range(2)]
    deleted_count = await repo.bulk_delete(filters)
    assert deleted_count == 2
    remaining = await repo.find()
    assert len(remaining) == 1
