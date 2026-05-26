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

    def set(self, field: FieldRef, value: Any) -> UpdateBuilder[T]:
        self._sets[field._field] = value
        return self

    def unset(self, field: FieldRef) -> UpdateBuilder[T]:
        self._unsets.append(field._field)
        return self

    def inc(self, field: FieldRef, amount: int | float) -> UpdateBuilder[T]:
        self._incs[field._field] = amount
        return self

    def push(self, field: FieldRef, value: Any) -> UpdateBuilder[T]:
        f = field._field
        if f not in self._pushes:
            self._pushes[f] = []
        self._pushes[f].append(value)
        return self

    def pull(self, field: FieldRef, value: Any) -> UpdateBuilder[T]:
        self._pull[field._field] = value
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
