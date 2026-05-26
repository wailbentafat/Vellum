from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection

from vellum.model import SoftDeleteMixin, VellumBaseModel
from vellum.query import QueryExpression, SortSpec


class QueryBuilder[T: VellumBaseModel]:

    def __init__(self, model_cls: type[T], collection: AsyncIOMotorCollection) -> None:
        self._model_cls = model_cls
        self._collection = collection
        self._filters: list[dict[str, Any]] = []
        self._sort_spec: list[SortSpec] = []
        self._skip_val: int = 0
        self._limit_val: int = 0
        self._include_deleted: bool = False

    def filter_expr(self, expr: QueryExpression | dict[str, Any]) -> QueryBuilder[T]:
        if isinstance(expr, QueryExpression):
            self._filters.append(expr.to_mongo_query())
        else:
            self._filters.append(expr)
        return self

    def sort(self, *specs: SortSpec) -> QueryBuilder[T]:
        self._sort_spec.extend(specs)
        return self

    def skip(self, n: int) -> QueryBuilder[T]:
        self._skip_val = n
        return self

    def limit(self, n: int) -> QueryBuilder[T]:
        self._limit_val = n
        return self

    def paginate(self, page: int = 1, size: int = 20) -> QueryBuilder[T]:
        page = max(page, 1)
        size = max(size, 1)
        self._skip_val = (page - 1) * size
        self._limit_val = size
        return self

    def include_deleted(self) -> QueryBuilder[T]:
        self._include_deleted = True
        return self

    def _build_query(self) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if self._filters:
            if len(self._filters) == 1:
                query.update(self._filters[0])
            else:
                query["$and"] = self._filters
        if issubclass(self._model_cls, SoftDeleteMixin) and not self._include_deleted:
            query["deleted_at"] = None
        return query

    async def execute(self) -> list[T]:
        query = self._build_query()
        cursor = self._collection.find(query)
        if self._sort_spec:
            cursor = cursor.sort([(s.field_name, s.direction) for s in self._sort_spec])
        cursor = cursor.skip(self._skip_val)
        if self._limit_val:
            cursor = cursor.limit(self._limit_val)
        raw_docs = await cursor.to_list(length=None)
        return [self._model_cls.from_mongo(doc) for doc in raw_docs]

    async def first(self) -> T | None:
        old_limit = self._limit_val
        self._limit_val = 1
        results = await self.execute()
        self._limit_val = old_limit
        return results[0] if results else None

    async def count(self) -> int:
        query = self._build_query()
        return await self._collection.count_documents(query)
