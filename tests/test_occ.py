import pytest
import pytest_asyncio

from vellum.exceptions import OptimisticLockError
from vellum.model import OptimisticConcurrencyMixin, VellumBaseModel
from vellum.repository import VellumRepository


class VersionedProduct(OptimisticConcurrencyMixin, VellumBaseModel):
    name: str
    stock: int

    class Settings:
        collection_name = "versioned_products"


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(VersionedProduct, db)


@pytest.mark.asyncio
async def test_version_starts_at_one(repo):
    p = VersionedProduct(name="Widget", stock=100)
    assert p.version == 1
    await repo.create(p)
    fetched = await repo.get(p.id)
    assert fetched.version == 1


@pytest.mark.asyncio
async def test_version_increments_on_update(repo):
    p = VersionedProduct(name="Widget", stock=100)
    await repo.create(p)
    p.stock = 90
    await repo.update(p.id, p)
    fetched = await repo.get(p.id)
    assert fetched.version == 2


@pytest.mark.asyncio
async def test_optimistic_lock_error_on_stale_update(repo):
    p = VersionedProduct(name="Gadget", stock=50)
    await repo.create(p)

    stale_copy = await repo.get(p.id)
    fresh_copy = await repo.get(p.id)

    fresh_copy.stock = 45
    await repo.update(fresh_copy.id, fresh_copy)

    stale_copy.stock = 40
    with pytest.raises(OptimisticLockError):
        await repo.update(stale_copy.id, stale_copy)
