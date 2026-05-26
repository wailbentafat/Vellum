from __future__ import annotations

import datetime
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from vellum.exceptions import DocumentNotFoundError
from vellum.model import VellumBaseModel

T = TypeVar("T", bound=VellumBaseModel)

SortDirection = int


class VellumRepository(Generic[T]):

    def __init__(self, model_cls: Type[T], database: AsyncIOMotorDatabase) -> None:
        self.model_cls = model_cls
        self.collection: AsyncIOMotorCollection = database[model_cls.get_collection_name()]

    async def create(self, item: T) -> T:
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        await item.before_insert()
        doc = item.to_mongo()
        result: InsertOneResult = await self.collection.insert_one(doc)
        if not result.inserted_id:
            raise RuntimeError("Insert did not return an inserted_id")
        await item.after_insert()
        return item

    async def get(self, doc_id: Union[UUID, str]) -> T:
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        raw: Optional[Dict[str, Any]] = await self.collection.find_one({"_id": query_id})
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return self.model_cls.from_mongo(raw)

    async def update(self, doc_id: Union[UUID, str], item: T) -> T:
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        await item.before_update()
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        doc = item.to_mongo()
        doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        result: UpdateResult = await self.collection.update_one(
            {"_id": query_id}, {"$set": doc}
        )
        if result.matched_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        await item.after_update()
        return item

    async def delete(self, doc_id: Union[UUID, str]) -> bool:
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        raw = await self.collection.find_one({"_id": query_id})
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        item = self.model_cls.from_mongo(raw)
        await item.before_delete()
        result: DeleteResult = await self.collection.delete_one({"_id": query_id})
        if result.deleted_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        await item.after_delete()
        return True

    async def find(
        self,
        query: Dict[str, Any] = {},
        skip: int = 0,
        limit: int = 0,
        sort: Optional[List[Tuple[str, SortDirection]]] = None,
    ) -> List[T]:
        skip = max(skip, 0)
        limit = max(limit, 0)
        cursor = self.collection.find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        raw_docs: List[Dict[str, Any]] = await cursor.to_list(length=None)
        return [self.model_cls.from_mongo(doc) for doc in raw_docs]

    async def count(self, query: Dict[str, Any] = {}) -> int:
        return await self.collection.count_documents(query)

    async def ensure_indexes(self) -> None:
        indexes = getattr(self.model_cls.Settings, "indexes", [])
        for index_spec in indexes:
            spec = dict(index_spec)
            key = spec.pop("key")
            await self.collection.create_index(key, **spec)
