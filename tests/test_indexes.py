from __future__ import annotations

import pytest

from vellum import Index, SortSpec, VellumBaseModel, VellumRepository


class Indexed(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "indexed"
        indexes = [
            {"key": [("name", 1)]},
        ]


class Indexed2(VellumBaseModel):
    name: str
    email: str
    price: float

    class Settings:
        collection_name = "indexed2"
        indexes = [
            Index("name"),
            Index("email", unique=True),
            Index("name", "price"),
        ]


class Indexed3(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "indexed3"

    @classmethod
    def __init_indexes__(cls):
        return [
            Index(cls.name, unique=True),
            Index(cls.email),
        ]


def test_index_init_with_fieldref():
    idx = Index("name")
    assert idx.to_dict() == {"key": [("name", 1)]}


def test_index_init_with_sortspec():
    idx = Index(SortSpec("name", 1), SortSpec("price", -1))
    assert idx.to_dict() == {"key": [("name", 1), ("price", -1)]}


def test_index_init_with_str():
    idx = Index("name")
    assert idx.to_dict() == {"key": [("name", 1)]}


def test_index_init_with_options():
    idx = Index("email", unique=True)
    assert idx.to_dict() == {"key": [("email", 1)], "unique": True}


def test_index_init_with_ttl():
    idx = Index("name", expireAfterSeconds=3600)
    d = idx.to_dict()
    assert d["key"] == [("name", 1)]
    assert d["expireAfterSeconds"] == 3600


def test_index_resolve_dict():
    raw = {"key": [("name", 1)], "unique": True}
    assert Index.resolve(raw) is raw


def test_index_resolve_index():
    idx = Index("email", unique=True)
    resolved = Index.resolve(idx)
    assert resolved == {"key": [("email", 1)], "unique": True}
    assert isinstance(resolved, dict)


def test_index_compound():
    idx = Index("name", "price")
    assert idx.to_dict() == {"key": [("name", 1), ("price", 1)]}


def test_index_mixed_directions():
    idx = Index(SortSpec("name", 1), SortSpec("price", -1))
    assert idx.to_dict() == {"key": [("name", 1), ("price", -1)]}


def test_index_validate_passes():
    idx = Index("name")
    idx.validate(Indexed2)


def test_index_validate_fails():
    idx = Index("nonexistent")
    with pytest.raises(ValueError, match="nonexistent"):
        idx.validate(Indexed2)


def test_index_to_dict_immutable():
    idx = Index("name", unique=True)
    d = idx.to_dict()
    d["extra"] = True
    assert "extra" not in idx.to_dict()


def test_init_indexes_classmethod():
    assert len(Indexed3.Settings.indexes) == 2
    d0 = Index.resolve(Indexed3.Settings.indexes[0])
    d1 = Index.resolve(Indexed3.Settings.indexes[1])
    assert d0["key"] == [("name", 1)]
    assert d0.get("unique") is True
    assert d1["key"] == [("email", 1)]


@pytest.mark.asyncio
async def test_ensure_indexes_from_init_indexes(db):
    repo = VellumRepository(Indexed3, db)
    await repo.ensure_indexes()
    indexes = await repo.list_indexes()
    assert len(indexes) >= 2


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
