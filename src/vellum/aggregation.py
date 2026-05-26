from __future__ import annotations

from typing import Any, Generic, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel

from vellum.query import FieldRef, QueryExpression, SortSpec, resolve_agg_refs

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT")


class AggregationPipeline(Generic[InputT, OutputT]):  # noqa: UP046

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        output_model: type[OutputT] | None = None,
    ) -> None:
        self._collection = collection
        self._stages: list[dict[str, Any]] = []
        self._output_model: type[OutputT] | None = output_model

    def match(
        self, query: QueryExpression | dict[str, Any]
    ) -> AggregationPipeline[InputT, OutputT]:
        q = query.to_mongo_query() if isinstance(query, QueryExpression) else query
        self._stages.append({"$match": q})
        return self

    def project[NewOutputT](
        self,
        projection: dict[str, Any] | dict[FieldRef, Any],
        output_model: type[NewOutputT] | None = None,
    ) -> AggregationPipeline[InputT, NewOutputT]:
        new = AggregationPipeline[InputT, NewOutputT](self._collection, output_model)
        resolved = resolve_agg_refs(projection)
        new._stages = [*self._stages, {"$project": resolved}]
        return new

    def group[NewOutputT](
        self,
        group_id: FieldRef | Any,
        output_model: type[NewOutputT] | None = None,
        **accumulators: Any,
    ) -> AggregationPipeline[InputT, NewOutputT]:
        new = AggregationPipeline[InputT, NewOutputT](self._collection, output_model)
        resolved_id = resolve_agg_refs(group_id)
        resolved_acc = resolve_agg_refs(accumulators)
        stage: dict[str, Any] = {"_id": resolved_id, **resolved_acc}
        new._stages = [*self._stages, {"$group": stage}]
        return new

    def sort(
        self, *specs: SortSpec
    ) -> AggregationPipeline[InputT, OutputT]:
        sort_dict = {s.field_name: s.direction for s in specs}
        self._stages.append({"$sort": sort_dict})
        return self

    def limit(self, n: int) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$limit": n})
        return self

    def skip(self, n: int) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$skip": n})
        return self

    def unwind(
        self, path: FieldRef | str, preserve_null_and_empty: bool = False
    ) -> AggregationPipeline[InputT, OutputT]:
        stage: Any = {"path": resolve_agg_refs(path)}
        if preserve_null_and_empty:
            stage["preserveNullAndEmptyArrays"] = True
        self._stages.append({"$unwind": stage})
        return self

    def add_fields(
        self, fields: dict[str, Any] | dict[FieldRef, Any]
    ) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$addFields": resolve_agg_refs(fields)})
        return self

    def set_fields(
        self, fields: dict[str, Any] | dict[FieldRef, Any]
    ) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$set": resolve_agg_refs(fields)})
        return self

    def replace_root(
        self, new_root: Any
    ) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$replaceRoot": {"newRoot": new_root}})
        return self

    def lookup(
        self,
        from_collection: str,
        local_field: FieldRef | str,
        foreign_field: FieldRef | str,
        as_field: FieldRef | str,
    ) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({
            "$lookup": {
                "from": from_collection,
                "localField": resolve_agg_refs(local_field),
                "foreignField": resolve_agg_refs(foreign_field),
                "as": resolve_agg_refs(as_field),
            }
        })
        return self

    def count_stage(self, output_field: str) -> AggregationPipeline[InputT, OutputT]:
        self._stages.append({"$count": output_field})
        return self

    async def execute(self) -> list[OutputT]:
        cursor = self._collection.aggregate(self._stages)
        raw: list[dict[str, Any]] = await cursor.to_list(length=None)
        if self._output_model is not None:
            return [self._output_model.model_validate(doc) for doc in raw]
        return raw  # type: ignore[return-value]
