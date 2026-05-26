from __future__ import annotations

import pytest

from vellum import VellumBaseModel, VellumRepository


class QBModel(VellumBaseModel):
    name: str
    email: str
    age: int

    class Settings:
        collection_name = "qb_test"


@pytest.fixture
async def repo(db):
    return VellumRepository(QBModel, db)


@pytest.mark.asyncio
async def test_query_filter_eq(repo):
    await repo.create(QBModel(name="Alice", email="alice@test.com", age=30))
    await repo.create(QBModel(name="Bob", email="bob@test.com", age=25))
    results = await repo.query().filter_expr(QBModel.fields.name == "Alice").execute()
    assert len(results) == 1
    assert results[0].name == "Alice"


@pytest.mark.asyncio
async def test_query_filter_icontains(repo):
    await repo.create(QBModel(name="HelloWorld", email="a@b.com", age=10))
    await repo.create(QBModel(name="Goodbye", email="c@d.com", age=20))
    results = (
        await repo.query()
        .filter_expr(QBModel.fields.name.regex("hello", "i"))
        .execute()
    )
    assert len(results) == 1
    assert results[0].name == "HelloWorld"


@pytest.mark.asyncio
async def test_query_sort_ascending(repo):
    await repo.create(QBModel(name="Beta", email="b@t.com", age=1))
    await repo.create(QBModel(name="Alpha", email="a@t.com", age=2))
    results = await repo.query().sort(QBModel.fields.name.asc()).execute()
    assert results[0].name == "Alpha"
    assert results[1].name == "Beta"


@pytest.mark.asyncio
async def test_query_sort_descending(repo):
    await repo.create(QBModel(name="Beta", email="b@t.com", age=1))
    await repo.create(QBModel(name="Alpha", email="a@t.com", age=2))
    results = await repo.query().sort(QBModel.fields.name.desc()).execute()
    assert results[0].name == "Beta"
    assert results[1].name == "Alpha"


@pytest.mark.asyncio
async def test_query_paginate(repo):
    for i in range(10):
        await repo.create(QBModel(name=f"User{i}", email=f"u{i}@t.com", age=i))
    page1 = await repo.query().sort(QBModel.fields.name.asc()).paginate(page=1, size=3).execute()
    assert len(page1) == 3
    page2 = await repo.query().sort(QBModel.fields.name.asc()).paginate(page=2, size=3).execute()
    assert len(page2) == 3
    assert page1[0].name != page2[0].name


@pytest.mark.asyncio
async def test_query_first(repo):
    await repo.create(QBModel(name="First", email="f@t.com", age=1))
    result = await repo.query().filter_expr(QBModel.fields.name == "First").first()
    assert result is not None
    assert result.name == "First"


@pytest.mark.asyncio
async def test_query_first_none(repo):
    result = await repo.query().filter_expr(QBModel.fields.name == "Nonexistent").first()
    assert result is None


@pytest.mark.asyncio
async def test_query_count(repo):
    await repo.create(QBModel(name="A", email="a@t.com", age=1))
    await repo.create(QBModel(name="B", email="b@t.com", age=2))
    cnt = await repo.query().filter_expr(QBModel.fields.age >= 1).count()
    assert cnt == 2


@pytest.mark.asyncio
async def test_query_filter_expr(repo):
    await repo.create(QBModel(name="Expr", email="e@t.com", age=5))
    await repo.create(QBModel(name="Other", email="o@t.com", age=10))
    results = await repo.query().filter_expr(QBModel.fields.age > 5).execute()
    assert len(results) == 1
    assert results[0].name == "Other"
