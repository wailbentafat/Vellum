from __future__ import annotations

from typing import Any
from uuid import UUID

MongoFieldPath = str


class QueryExpression:

    def to_mongo_query(self) -> dict[str, Any]:
        raise NotImplementedError

    def __and__(self, other: QueryExpression) -> And:
        return And(self, other)

    def __or__(self, other: QueryExpression) -> Or:
        return Or(self, other)

    def __invert__(self) -> Not:
        return Not(self)


class FieldQueryExpression(QueryExpression):

    def __init__(self, field: MongoFieldPath, value: Any) -> None:
        self.field = field
        self.value = value

    def _to_mongo_value(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        return value


class Eq(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: self._to_mongo_value(self.value)}


class Ne(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$ne": self._to_mongo_value(self.value)}}


class Gt(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$gt": self._to_mongo_value(self.value)}}


class Gte(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$gte": self._to_mongo_value(self.value)}}


class Lt(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$lt": self._to_mongo_value(self.value)}}


class Lte(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$lte": self._to_mongo_value(self.value)}}


class In(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$in requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$in": converted}}


class NotIn(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$nin requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$nin": converted}}


class All(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$all requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$all": converted}}


class Size(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$size": self.value}}


class ElemMatch(QueryExpression):

    def __init__(self, field: MongoFieldPath, expression: QueryExpression) -> None:
        self.field = field
        self.expression = expression

    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$elemMatch": self.expression.to_mongo_query()}}


class Exists(FieldQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$exists": bool(self.value)}}


class Regex(QueryExpression):

    def __init__(
        self, field: MongoFieldPath, pattern: str, options: str | None = None
    ) -> None:
        self.field = field
        self.pattern = pattern
        self.options = options

    def to_mongo_query(self) -> dict[str, Any]:
        expr: dict[str, Any] = {"$regex": self.pattern}
        if self.options:
            expr["$options"] = self.options
        return {self.field: expr}


class LogicalQueryExpression(QueryExpression):

    def __init__(self, *expressions: QueryExpression) -> None:
        if not all(isinstance(e, QueryExpression) for e in expressions):
            raise TypeError("All arguments must be QueryExpression instances.")
        self.expressions = expressions


class And(LogicalQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {"$and": [e.to_mongo_query() for e in self.expressions]}


class Or(LogicalQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {"$or": [e.to_mongo_query() for e in self.expressions]}


class Nor(LogicalQueryExpression):
    def to_mongo_query(self) -> dict[str, Any]:
        return {"$nor": [e.to_mongo_query() for e in self.expressions]}


class Not(LogicalQueryExpression):

    def __init__(self, expression: QueryExpression) -> None:
        super().__init__(expression)

    def to_mongo_query(self) -> dict[str, Any]:
        return {"$nor": [e.to_mongo_query() for e in self.expressions]}


def eq(field: MongoFieldPath, value: Any) -> Eq:
    return Eq(field, value)


def ne(field: MongoFieldPath, value: Any) -> Ne:
    return Ne(field, value)


def gt(field: MongoFieldPath, value: Any) -> Gt:
    return Gt(field, value)


def gte(field: MongoFieldPath, value: Any) -> Gte:
    return Gte(field, value)


def lt(field: MongoFieldPath, value: Any) -> Lt:
    return Lt(field, value)


def lte(field: MongoFieldPath, value: Any) -> Lte:
    return Lte(field, value)


def in_(field: MongoFieldPath, values: list[Any]) -> In:
    return In(field, values)


def not_in(field: MongoFieldPath, values: list[Any]) -> NotIn:
    return NotIn(field, values)


def exists(field: MongoFieldPath, value: bool = True) -> Exists:
    return Exists(field, value)


def regex(field: MongoFieldPath, pattern: str, options: str | None = None) -> Regex:
    return Regex(field, pattern, options)


def size(field: MongoFieldPath, count: int) -> Size:
    return Size(field, count)


def all_(field: MongoFieldPath, values: list[Any]) -> All:
    return All(field, values)


def elem_match(field: MongoFieldPath, expression: QueryExpression) -> ElemMatch:
    return ElemMatch(field, expression)
