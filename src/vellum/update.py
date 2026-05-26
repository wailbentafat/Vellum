from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorCollection

from vellum.query import FieldRef


class UpdateBuilder[T]:

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        doc_id: UUID | str,
        session: AsyncIOMotorClientSession | None = None,
    ) -> None:
        self._collection = collection
        self._doc_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        self._session = session
        self._sets: dict[str, Any] = {}
        self._unsets: list[str] = []
        self._incs: dict[str, int | float] = {}
        self._pushes: dict[str, Any] = {}
        self._pull: dict[str, Any] = {}

    def set(self, field: FieldRef | str, value: Any) -> UpdateBuilder[T]:
        name = field._field if isinstance(field, FieldRef) else field
        self._sets[name] = value
        return self

    def unset(self, field: FieldRef | str) -> UpdateBuilder[T]:
        name = field._field if isinstance(field, FieldRef) else field
        self._unsets.append(name)
        return self

    def inc(self, field: FieldRef | str, amount: int | float) -> UpdateBuilder[T]:
        name = field._field if isinstance(field, FieldRef) else field
        self._incs[name] = amount
        return self

    def push(self, field: FieldRef | str, value: Any) -> UpdateBuilder[T]:
        name = field._field if isinstance(field, FieldRef) else field
        if name not in self._pushes:
            self._pushes[name] = []
        self._pushes[name].append(value)
        return self

    def pull(self, field: FieldRef | str, value: Any) -> UpdateBuilder[T]:
        name = field._field if isinstance(field, FieldRef) else field
        self._pull[name] = value
        return self

    def _build_update(self) -> dict[str, Any]:
        update: dict[str, Any] = {}
        if self._sets:
            self._sets["updated_at"] = datetime.datetime.now(datetime.UTC)
            update["$set"] = self._sets
        if self._unsets:
            update["$unset"] = {f: "" for f in self._unsets}
        if self._incs:
            update["$inc"] = self._incs
        if self._pushes:
            update["$push"] = self._pushes
        if self._pull:
            update["$pull"] = self._pull
        return update

    async def execute(self) -> dict[str, Any] | None:
        update = self._build_update()
        if not update:
            return None
        result = await self._collection.find_one_and_update(
            {"_id": self._doc_id},
            update,
            return_document=True,
            session=self._session,
        )
        return result
