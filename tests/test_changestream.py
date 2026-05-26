from __future__ import annotations

import asyncio

import pytest

from vellum import VellumBaseModel, VellumRepository
from vellum.changestream import ChangeEvent


class WatchModel(VellumBaseModel):
    name: str

    class Settings:
        collection_name = "watch_test"


@pytest.fixture
async def repo(db):
    return VellumRepository(WatchModel, db)


@pytest.mark.skip(reason="Requires a MongoDB replica set, not a standalone server")
@pytest.mark.asyncio
async def test_watch_receives_insert_event(repo):
    stream = repo.watch()
    events: list[ChangeEvent] = []
    stream.on("insert", lambda e: events.append(e))
    stream.start()
    await asyncio.sleep(0.2)
    await repo.create(WatchModel(name="StreamTest"))
    await asyncio.sleep(0.3)
    await stream.stop()
    assert len(events) >= 1
    assert events[0].operation_type == "insert"
    assert events[0].doc_id is not None
    if events[0].model:
        assert events[0].model.name == "StreamTest"


@pytest.mark.skip(reason="Requires a MongoDB replica set, not a standalone server")
@pytest.mark.asyncio
async def test_watch_iterates_events(repo):
    stream = repo.watch()
    stream.start()
    await asyncio.sleep(0.2)
    await repo.create(WatchModel(name="IterTest"))
    await asyncio.sleep(0.3)
    events = []
    async for event in stream:
        events.append(event)
        break
    await stream.stop()
    assert len(events) >= 1
    assert events[0].operation_type == "insert"


@pytest.mark.skip(reason="Requires a MongoDB replica set, not a standalone server")
@pytest.mark.asyncio
async def test_watch_wildcard_handler(repo):
    stream = repo.watch()
    events: list[ChangeEvent] = []
    stream.on("*", lambda e: events.append(e))
    stream.start()
    await asyncio.sleep(0.2)
    await repo.create(WatchModel(name="WildTest"))
    await asyncio.sleep(0.3)
    await stream.stop()
    assert len(events) >= 1
