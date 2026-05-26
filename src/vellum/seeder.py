from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


class Factory[T: VellumBaseModel]:

    def __init__(self, model_cls: type[T], builder: Callable[[int], dict[str, Any]]) -> None:
        self._model_cls = model_cls
        self._builder = builder

    def build(self, index: int = 0) -> T:
        data = self._builder(index)
        data.setdefault("id", uuid4())
        return self._model_cls(**data)


class Seeder:

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def seed[T: VellumBaseModel](
        self,
        model_cls: type[T],
        count: int = 10,
        builder: Callable[[int], dict[str, Any]] | None = None,
        factory: Factory[T] | None = None,
        batch_size: int = 100,
    ) -> list[T]:
        repo = VellumRepository(model_cls, self._db)
        items: list[T] = []
        f = factory or Factory(model_cls, builder or (lambda i: {}))
        for i in range(count):
            items.append(f.build(i))
        created: list[T] = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            created.extend(await repo.bulk_create(batch))
        return created

    async def truncate(self, model_cls: type[VellumBaseModel]) -> int:
        col = self._db[model_cls.get_collection_name()]
        result = await col.delete_many({})
        return result.deleted_count

    async def truncate_all(self, models: list[type[VellumBaseModel]]) -> dict[str, int]:
        results: dict[str, int] = {}
        for model_cls in models:
            results[model_cls.__name__] = await self.truncate(model_cls)
        return results
