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
from pymongo.operations import DeleteOne, UpdateOne
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from vellum.changestream import ChangeStream
from vellum.exceptions import DocumentNotFoundError, OptimisticLockError
from vellum.model import OptimisticConcurrencyMixin, SoftDeleteMixin, VellumBaseModel
from vellum.query import Index, QueryExpression, SortSpec
from vellum.querybuilder import QueryBuilder
from vellum.update import UpdateBuilder

SortDirection = int
SortInput = SortSpec | tuple[str, int]

QueryInput = QueryExpression | dict[str, Any]


class VellumRepository[T: VellumBaseModel]:

    def __init__(self, model_cls: type[T], database: AsyncIOMotorDatabase) -> None:
        self.model_cls = model_cls
        self.collection: AsyncIOMotorCollection = database[model_cls.get_collection_name()]

    @staticmethod
    def _resolve_query(query: QueryInput) -> dict[str, Any]:
        return query.to_mongo_query() if isinstance(query, QueryExpression) else dict(query)

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

    def update_builder(
        self, doc_id: UUID | str, session: AsyncIOMotorClientSession | None = None
    ) -> UpdateBuilder[T]:
        return UpdateBuilder[T](self.collection, doc_id, session)

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
        query: QueryInput = {},
        skip: int = 0,
        limit: int = 0,
        sort: list[SortSpec] | None = None,
        include_deleted: bool = False,
    ) -> list[T]:
        skip = max(skip, 0)
        limit = max(limit, 0)
        effective_query = self._resolve_query(query)
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            effective_query["deleted_at"] = None
        cursor = self.collection.find(effective_query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort([(s.field_name, s.direction) for s in sort])
        raw_docs: list[dict[str, Any]] = await cursor.to_list(length=None)
        return [self.model_cls.from_mongo(doc) for doc in raw_docs]

    async def find_cursor(
        self,
        query: QueryInput = {},
        sort: list[SortSpec] | None = None,
        batch_size: int = 100,
        include_deleted: bool = False,
    ) -> AsyncGenerator[T, None]:
        effective_query = self._resolve_query(query)
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            effective_query["deleted_at"] = None
        cursor = self.collection.find(effective_query, batch_size=batch_size)
        if sort:
            cursor = cursor.sort([(s.field_name, s.direction) for s in sort])
        async for doc in cursor:
            yield self.model_cls.from_mongo(doc)

    def query(self) -> QueryBuilder[T]:
        return QueryBuilder(self.model_cls, self.collection)

    def watch(
        self,
        pipeline: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChangeStream[T]:
        raw_stream = self.collection.watch(pipeline or [], **kwargs)
        return ChangeStream(self.model_cls, raw_stream)

    async def get(self, doc_id: UUID | str, include_deleted: bool = False) -> T:
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        mongo_filter: dict[str, Any] = {"_id": query_id}
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            mongo_filter["deleted_at"] = None
        raw = await self.collection.find_one(mongo_filter)
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return self.model_cls.from_mongo(raw)

    async def find_one(
        self,
        query: QueryInput = {},
        sort: list[SortSpec] | None = None,
        include_deleted: bool = False,
    ) -> T | None:
        effective_query = self._resolve_query(query)
        if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
            effective_query["deleted_at"] = None
        cursor = self.collection.find(effective_query).limit(1)
        if sort:
            cursor = cursor.sort([(s.field_name, s.direction) for s in sort])
        raw = await cursor.to_list(length=1)
        if not raw:
            return None
        return self.model_cls.from_mongo(raw[0])

    async def find_or_create(
        self,
        query: QueryInput,
        defaults: dict[str, Any] = {},
        include_deleted: bool = False,
    ) -> T:
        existing = await self.find_one(query, include_deleted=include_deleted)
        if existing is not None:
            return existing
        resolved = self._resolve_query(query)
        merged = {**resolved, **defaults}
        item = self.model_cls(**merged)
        return await self.create(item)

    async def upsert(
        self,
        query: QueryInput,
        item: T,
        session: AsyncIOMotorClientSession | None = None,
    ) -> T:
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        doc = item.to_mongo()
        doc["updated_at"] = datetime.datetime.now(datetime.UTC)
        doc.pop("_id", None)
        doc.pop("created_at", None)
        now = datetime.datetime.now(datetime.UTC)
        result: UpdateResult = await self.collection.update_one(
            self._resolve_query(query),
            {"$set": doc, "$setOnInsert": {"_id": str(item.id), "created_at": now}},
            upsert=True,
            session=session,
        )
        if result.upserted_id is not None:
            item.id = UUID(str(result.upserted_id))
        return item

    async def populate(
        self,
        item: T,
        field_name: str,
        repo: VellumRepository,
    ) -> T:
        field_value = getattr(item, field_name, None)
        if field_value is None:
            return item
        if isinstance(field_value, UUID):
            referenced = await repo.get(field_value)
            setattr(item, field_name, referenced)
        return item

    async def populate_many(
        self,
        items: list[T],
        field_name: str,
        repo: VellumRepository,
    ) -> list[T]:
        ids: set[UUID] = set()
        for item in items:
            val = getattr(item, field_name, None)
            if isinstance(val, UUID):
                ids.add(val)
        if not ids:
            return items
        refs = await repo.find({"_id": {"$in": [str(i) for i in ids]}})
        ref_map = {r.id: r for r in refs}
        for item in items:
            val = getattr(item, field_name, None)
            if isinstance(val, UUID) and val in ref_map:
                setattr(item, field_name, ref_map[val])
        return items

    async def count(self, query: QueryInput = {}, include_deleted: bool = False) -> int:
        effective_query = self._resolve_query(query)
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

    async def bulk_create(
        self, items: list[T], session: AsyncIOMotorClientSession | None = None
    ) -> list[T]:
        for item in items:
            if not isinstance(item, self.model_cls):
                raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
            await item.before_insert()
        docs = [item.to_mongo() for item in items]
        await self.collection.insert_many(docs, session=session)
        for item in items:
            await item.after_insert()
        return items

    async def bulk_update(
        self, items: list[T], session: AsyncIOMotorClientSession | None = None
    ) -> list[T]:
        operations: list[UpdateOne] = []
        now = datetime.datetime.now(datetime.UTC)
        for item in items:
            if not isinstance(item, self.model_cls):
                raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
            await item.before_update()
            doc = item.to_mongo()
            doc["updated_at"] = now
            query_id = str(item.id)
            operations.append(UpdateOne({"_id": query_id}, {"$set": doc}))
        await self.collection.bulk_write(operations, session=session)
        for item in items:
            await item.after_update()
        return items

    async def bulk_delete(
        self,
        filters: list[dict[str, Any]],
        session: AsyncIOMotorClientSession | None = None,
    ) -> int:
        operations = [DeleteOne(f) for f in filters]
        result = await self.collection.bulk_write(operations, session=session)
        return result.deleted_count

    async def ensure_indexes(self) -> None:
        indexes = getattr(self.model_cls.Settings, "indexes", [])
        for index_spec in indexes:
            if isinstance(index_spec, Index):
                index_spec.validate(self.model_cls)
            spec = dict(Index.resolve(index_spec))
            key = spec.pop("key")
            await self.collection.create_index(key, **spec)

    async def create_index(
        self,
        keys: list[tuple[str, int]],
        **kwargs: Any,
    ) -> str:
        return await self.collection.create_index(keys, **kwargs)

    async def drop_index(self, name: str) -> None:
        await self.collection.drop_index(name)

    async def list_indexes(self) -> list[dict[str, Any]]:
        cursor = self.collection.list_indexes()
        return [idx async for idx in cursor]

    @staticmethod
    def _json_type_to_bson(json_type: str | None, fmt: str | None = None) -> str:
        if fmt == "date-time":
            return "date"
        mapping: dict[str, str] = {
            "string": "string",
            "number": "double",
            "integer": "long",
            "boolean": "bool",
            "array": "array",
            "object": "object",
            "null": "null",
        }
        return mapping.get(json_type or "string", "string")

    def _build_json_schema(self) -> dict[str, Any]:
        schema = self.model_cls.model_json_schema(by_alias=True)
        properties: dict[str, Any] = {}
        required: list[str] = []
        definitions: dict[str, Any] = schema.get("$defs", {})

        for field_name, field_schema in schema.get("properties", {}).items():
            prop: dict[str, Any] = {}
            if "$ref" in field_schema:
                ref_key = field_schema["$ref"].split("/")[-1]
                ref_schema = definitions.get(ref_key, {})
                if ref_schema.get("type") == "object":
                    prop["bsonType"] = "object"
                    ref_props: dict[str, Any] = {}
                    for ref_field, ref_fs in ref_schema.get("properties", {}).items():
                        ref_props[ref_field] = {
                            "bsonType": self._json_type_to_bson(
                                ref_fs.get("type"), ref_fs.get("format")
                            )
                        }
                    if ref_props:
                        prop["properties"] = ref_props
                else:
                    prop["bsonType"] = self._json_type_to_bson(
                        ref_schema.get("type"), ref_schema.get("format")
                    )
            elif field_schema.get("type") == "array":
                prop["bsonType"] = "array"
                items = field_schema.get("items", {})
                if "$ref" in items:
                    prop["description"] = f"Array of {items['$ref'].split('/')[-1]}"
                elif items.get("type"):
                    prop["items"] = {
                        "bsonType": self._json_type_to_bson(
                            items.get("type"), items.get("format")
                        )
                    }
            else:
                prop["bsonType"] = self._json_type_to_bson(
                    field_schema.get("type"), field_schema.get("format")
                )
            if field_name in schema.get("required", []):
                required.append(field_name)
            properties[field_name] = prop

        return {
            "$jsonSchema": {
                "bsonType": "object",
                "required": required,
                "properties": properties,
                "additionalProperties": False,
            }
        }

    async def set_schema_validation(self) -> None:
        validator = self._build_json_schema()
        collection_name = self.model_cls.get_collection_name()
        existing = await self.collection.database.list_collection_names()
        if collection_name in existing:
            await self.collection.database.command(
                "collMod",
                collection_name,
                validator=validator,
                validationLevel="strict",
                validationAction="error",
            )
        else:
            await self.collection.database.create_collection(
                collection_name,
                validator=validator,
                validationLevel="strict",
                validationAction="error",
            )
