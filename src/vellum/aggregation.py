from __future__ import annotations

from typing import Any, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class AggregationPipeline:

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        output_model: type[BaseModel] | None = None,
    ) -> None:
        self._collection = collection
        self._stages: list[dict[str, Any]] = []
        self._output_model = output_model

    def match(self, query: dict[str, Any]) -> AggregationPipeline:
        self._stages.append({"$match": query})
        return self

    def project(
        self,
        projection: dict[str, Any],
        output_model: type[BaseModel] | None = None,
    ) -> AggregationPipeline:
        self._stages.append({"$project": projection})
        if output_model is not None:
            self._output_model = output_model
        return self

    def group(
        self,
        group_id: Any,
        output_model: type[BaseModel] | None = None,
        **accumulators: Any,
    ) -> AggregationPipeline:
        stage: dict[str, Any] = {"_id": group_id, **accumulators}
        self._stages.append({"$group": stage})
        if output_model is not None:
            self._output_model = output_model
        return self

    def sort(self, sort_spec: list[tuple[str, int]]) -> AggregationPipeline:
        self._stages.append({"$sort": dict(sort_spec)})
        return self

    def limit(self, n: int) -> AggregationPipeline:
        self._stages.append({"$limit": n})
        return self

    def skip(self, n: int) -> AggregationPipeline:
        self._stages.append({"$skip": n})
        return self

    def unwind(self, path: str, preserve_null_and_empty: bool = False) -> AggregationPipeline:
        stage: Any = {"path": path}
        if preserve_null_and_empty:
            stage["preserveNullAndEmptyArrays"] = True
        self._stages.append({"$unwind": stage})
        return self

    def add_fields(self, fields: dict[str, Any]) -> AggregationPipeline:
        self._stages.append({"$addFields": fields})
        return self

    def set(self, fields: dict[str, Any]) -> AggregationPipeline:
        self._stages.append({"$set": fields})
        return self

    def replace_root(self, new_root: Any) -> AggregationPipeline:
        self._stages.append({"$replaceRoot": {"newRoot": new_root}})
        return self

    def lookup(
        self,
        from_collection: str,
        local_field: str,
        foreign_field: str,
        as_field: str,
    ) -> AggregationPipeline:
        self._stages.append({
            "$lookup": {
                "from": from_collection,
                "localField": local_field,
                "foreignField": foreign_field,
                "as": as_field,
            }
        })
        return self

    def count_stage(self, output_field: str) -> AggregationPipeline:
        self._stages.append({"$count": output_field})
        return self

    async def execute(self) -> list[Any]:
        cursor = self._collection.aggregate(self._stages)
        raw: list[dict[str, Any]] = await cursor.to_list(length=None)
        if self._output_model is not None:
            return [self._output_model.model_validate(doc) for doc in raw]
        return raw
