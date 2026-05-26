from __future__ import annotations

import pytest

from vellum import VellumBaseModel
from vellum.seeder import Factory, Seeder


class SeedModel(VellumBaseModel):
    name: str
    value: int = 0

    class Settings:
        collection_name = "seed_test"


@pytest.fixture
async def seeder(db):
    return Seeder(db)


@pytest.mark.asyncio
async def test_seeder_creates_items(seeder):
    items = await seeder.seed(
        SeedModel, count=5, builder=lambda i: {"name": f"Seed{i}", "value": i}
    )
    assert len(items) == 5
    assert items[0].name == "Seed0"
    assert items[4].name == "Seed4"


@pytest.mark.asyncio
async def test_seeder_with_factory(seeder):
    factory = Factory(SeedModel, lambda i: {"name": f"Factory{i}", "value": i * 10})
    items = await seeder.seed(SeedModel, count=3, factory=factory)
    assert len(items) == 3
    assert items[2].value == 20


@pytest.mark.asyncio
async def test_factory_build():
    factory = Factory(SeedModel, lambda i: {"name": f"F{i}", "value": i})
    item = factory.build(5)
    assert item.name == "F5"
    assert item.value == 5


@pytest.mark.asyncio
async def test_truncate(seeder):
    await seeder.seed(SeedModel, count=3, builder=lambda i: {"name": f"T{i}"})
    deleted = await seeder.truncate(SeedModel)
    assert deleted == 3
