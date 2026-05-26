from __future__ import annotations

import pytest

from vellum import VellumBaseModel, VellumRepository


class Indexed(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "indexed"
        indexes = [
            {"key": [("name", 1)]},
        ]


@pytest.fixture
async def repo(db):
    return VellumRepository(Indexed, db)


@pytest.mark.asyncio
async def test_create_and_list_index(repo):
    name = await repo.create_index([("email", 1)], unique=True)
    assert isinstance(name, str)
    indexes = await repo.list_indexes()
    index_names = [i["name"] for i in indexes]
    assert name in index_names


@pytest.mark.asyncio
async def test_drop_index(repo):
    name = await repo.create_index([("email", 1)])
    await repo.drop_index(name)
    indexes = await repo.list_indexes()
    index_names = [i["name"] for i in indexes]
    assert name not in index_names


@pytest.mark.asyncio
async def test_ensure_indexes_from_settings(repo):
    await repo.ensure_indexes()
    indexes = await repo.list_indexes()
    assert len(indexes) >= 1


@pytest.mark.asyncio
async def test_create_ttl_index(repo):
    name = await repo.create_index([("created_at", 1)], expireAfterSeconds=3600)
    indexes = await repo.list_indexes()
    match = [i for i in indexes if i["name"] == name]
    assert match
    assert match[0].get("expireAfterSeconds") == 3600
