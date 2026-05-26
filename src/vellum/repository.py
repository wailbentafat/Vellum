from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import datetime
from typing import Any
from uuid import UUID

from motor.motor_asyncio import (
    AsyncIOMotorClientSession,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from vellum.exceptions import DocumentNotFoundError, OptimisticLockError
from vellum.model import OptimisticConcurrencyMixin, SoftDeleteMixin, VellumBaseModel

SortDirection = int


class VellumRepository[T: VellumBaseModel]:

    def __init__(self, model_cls: type[T], database: AsyncIOMotorDatabase) -> None:
        self.model_cls = model_cls
        self.collection: AsyncIOMotorCollection = database[model_cls.get_collection_name()]

    async def create(self, item: T, session: AsyncIOMotorClientSession | None = None) -> T:
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        await item.before_insert()
        doc = item.to_mongo()
        result: InsertOneResult = await self.collection.insert_one(doc, session=session)
        if not result.inserted_id:
            raise RuntimeError("Insert did not return an inserted_id")
        await item.after_insert()
        return item

    async def update(
        self, doc_id: UUID | str, item: T, session: AsyncIOMotorClientSession | None = None
    ) -> T:
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        await item.before_update()
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        doc = item.to_mongo()
        doc["updated_at"] = datetime.datetime.now(datetime.UTC)

        if isinstance(item, OptimisticConcurrencyMixin):
            current_version = item.version
            doc["version"] = current_version + 1
            mongo_filter = {"_id": query_id, "version": current_version}
        else:
            mongo_filter = {"_id": query_id}

        result: UpdateResult = await self.collection.update_one(
            mongo_filter, {"$set": doc}, session=session
        )
        if result.matched_count == 0:
            if isinstance(item, OptimisticConcurrencyMixin):
                raise OptimisticLockError(
                    f"Document id={doc_id} was modified by another process (version mismatch)."
                )
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")

        if isinstance(item, OptimisticConcurrencyMixin):
            item.version = current_version + 1

        await item.after_update()
        return item

    async def delete(
        self, doc_id: UUID | str, session: AsyncIOMotorClientSession | None = None
    ) -> bool:
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        raw = await self.collection.find_one({"_id": query_id}, session=session)
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        item = self.model_cls.from_mongo(raw)
        await item.before_delete()
        result: DeleteResult = await self.collection.delete_one({"_id": query_id}, session=session)
        if result.deleted_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        await item.after_delete()
        return True

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncIOMotorClientSession, None]:
        async with await self.collection.database.client.start_session() as session:
            async with session.start_transaction():
                yield session

    async def find(
        self,
        query: dict[str, Any] = {},
        skip: int = 0,
        limit: int = 0,
        sort: list[tuple[str, SortDirection]] | None = None,
        include_deleted: bool = False,
    ) -> list[T]:
        skip = max(skip, 0)
        limit = max(limit, 0)
        effective_query = dict(query)
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            effective_query["deleted_at"] = None
        cursor = self.collection.find(effective_query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        raw_docs: list[dict[str, Any]] = await cursor.to_list(length=None)
        return [self.model_cls.from_mongo(doc) for doc in raw_docs]

    async def get(self, doc_id: UUID | str, include_deleted: bool = False) -> T:
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        mongo_filter: dict[str, Any] = {"_id": query_id}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            mongo_filter["deleted_at"] = None
        raw = await self.collection.find_one(mongo_filter)
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return self.model_cls.from_mongo(raw)

    async def count(self, query: dict[str, Any] = {}, include_deleted: bool = False) -> int:
        effective_query = dict(query)
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            effective_query["deleted_at"] = None
        return await self.collection.count_documents(effective_query)

    async def soft_delete(self, doc_id: UUID | str) -> bool:
        if not issubclass(self.model_cls, SoftDeleteMixin):
            raise TypeError(
                f"{self.model_cls.__name__} does not use SoftDeleteMixin. "
                "Use delete() for hard deletes."
            )
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        now = datetime.datetime.now(datetime.UTC)
        result = await self.collection.update_one(
            {"_id": query_id}, {"$set": {"deleted_at": now}}
        )
        if result.matched_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return True

    async def restore(self, doc_id: UUID | str) -> bool:
        if not issubclass(self.model_cls, SoftDeleteMixin):
            raise TypeError(f"{self.model_cls.__name__} does not use SoftDeleteMixin.")
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        result = await self.collection.update_one(
            {"_id": query_id}, {"$set": {"deleted_at": None}}
        )
        if result.matched_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return True

    async def ensure_indexes(self) -> None:
        indexes = getattr(self.model_cls.Settings, "indexes", [])
        for index_spec in indexes:
            spec = dict(index_spec)
            key = spec.pop("key")
            await self.collection.create_index(key, **spec)
