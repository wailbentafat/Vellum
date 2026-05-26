from __future__ import annotations

import pytest

from vellum import VellumBaseModel, VellumRepository
from vellum.caching import CachedRepository


class CacheModel(VellumBaseModel):
    name: str

    class Settings:
        collection_name = "cache_test"


@pytest.fixture
async def repo(db):
    return CachedRepository(VellumRepository(CacheModel, db), ttl=300)


@pytest.mark.asyncio
async def test_cached_get(repo):
    item = await repo.create(CacheModel(name="Cached"))
    # First call populates cache
    f1 = await repo.get(item.id)
    assert f1.name == "Cached"
    # Second call should hit cache
    f2 = await repo.get(item.id)
    assert f2.name == "Cached"


@pytest.mark.asyncio
async def test_cache_invalidation(repo):
    item = await repo.create(CacheModel(name="Evict"))
    await repo.get(item.id)
    repo.invalidate(item.id)
    # Should re-fetch from DB
    f2 = await repo.get(item.id)
    assert f2.name == "Evict"


@pytest.mark.asyncio
async def test_clear_cache(repo):
    item = await repo.create(CacheModel(name="Clear"))
    await repo.get(item.id)
    repo.clear_cache()
    # Underlying repo works
    f2 = await repo.get(item.id)
    assert f2.name == "Clear"
