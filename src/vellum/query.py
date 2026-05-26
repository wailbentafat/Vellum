from __future__ import annotations

from typing import Any, NamedTuple
from uuid import UUID

MongoFieldPath = str


class SortSpec(NamedTuple):
    field_name: str
    direction: int


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


GeoJSONType = dict[str, Any]


class Near(QueryExpression):
    def __init__(
        self,
        field: MongoFieldPath,
        coordinates: tuple[float, float],
        max_distance: float | None = None,
        min_distance: float | None = None,
    ) -> None:
        self.field = field
        self.coordinates = coordinates
        self.max_distance = max_distance
        self.min_distance = min_distance

    def to_mongo_query(self) -> dict[str, Any]:
        geo: dict[str, Any] = {
            "$geometry": {"type": "Point", "coordinates": list(self.coordinates)}
        }
        if self.max_distance is not None:
            geo["$maxDistance"] = self.max_distance
        if self.min_distance is not None:
            geo["$minDistance"] = self.min_distance
        return {self.field: {"$near": geo}}


class NearSphere(QueryExpression):
    def __init__(
        self,
        field: MongoFieldPath,
        coordinates: tuple[float, float],
        max_distance: float | None = None,
        min_distance: float | None = None,
    ) -> None:
        self.field = field
        self.coordinates = coordinates
        self.max_distance = max_distance
        self.min_distance = min_distance

    def to_mongo_query(self) -> dict[str, Any]:
        geo: dict[str, Any] = {
            "$geometry": {"type": "Point", "coordinates": list(self.coordinates)}
        }
        if self.max_distance is not None:
            geo["$maxDistance"] = self.max_distance
        if self.min_distance is not None:
            geo["$minDistance"] = self.min_distance
        return {self.field: {"$nearSphere": geo}}


class GeoWithin(QueryExpression):
    def __init__(self, field: MongoFieldPath, geometry: GeoJSONType) -> None:
        self.field = field
        self.geometry = geometry

    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$geoWithin": {"$geometry": self.geometry}}}


class GeoIntersects(QueryExpression):
    def __init__(self, field: MongoFieldPath, geometry: GeoJSONType) -> None:
        self.field = field
        self.geometry = geometry

    def to_mongo_query(self) -> dict[str, Any]:
        return {self.field: {"$geoIntersects": {"$geometry": self.geometry}}}


class TextSearch(QueryExpression):
    def __init__(
        self,
        search: str,
        language: str | None = None,
        case_sensitive: bool | None = None,
        diacritic_sensitive: bool | None = None,
    ) -> None:
        self.search = search
        self.language = language
        self.case_sensitive = case_sensitive
        self.diacritic_sensitive = diacritic_sensitive

    def to_mongo_query(self) -> dict[str, Any]:
        expr: dict[str, Any] = {"$search": self.search}
        if self.language is not None:
            expr["$language"] = self.language
        if self.case_sensitive is not None:
            expr["$caseSensitive"] = self.case_sensitive
        if self.diacritic_sensitive is not None:
            expr["$diacriticSensitive"] = self.diacritic_sensitive
        return {"$text": expr}

    def __and__(self, other: QueryExpression) -> And:
        raise TypeError("$text cannot be combined with logical operators via &")

    def __or__(self, other: QueryExpression) -> Or:
        raise TypeError("$text cannot be combined with logical operators via |")

    def __invert__(self) -> Not:
        raise TypeError("$text cannot be combined with logical operators via ~")


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


class FieldsProxy:
    def __init__(self, model_cls: type) -> None:
        self._model_cls = model_cls

    def __getattr__(self, name: str) -> FieldRef:
        if name in self._model_cls.model_fields:
            return FieldRef(name)
        raise AttributeError(f"{self._model_cls.__name__} has no field '{name}'")


class FieldRef:
    def __init__(self, field_name: str) -> None:
        self._field = field_name

    def __getattr__(self, name: str) -> FieldRef:
        if name.startswith("_"):
            raise AttributeError(name)
        return FieldRef(f"{self._field}.{name}")

    def __eq__(self, other: Any) -> Eq:
        return Eq(self._field, other)

    def __ne__(self, other: Any) -> Ne:
        return Ne(self._field, other)

    def __lt__(self, other: Any) -> Lt:
        return Lt(self._field, other)

    def __le__(self, other: Any) -> Lte:
        return Lte(self._field, other)

    def __gt__(self, other: Any) -> Gt:
        return Gt(self._field, other)

    def __ge__(self, other: Any) -> Gte:
        return Gte(self._field, other)

    def __hash__(self) -> int:
        return hash(self._field)

    def __pos__(self) -> SortSpec:
        return SortSpec(self._field, 1)

    def __neg__(self) -> SortSpec:
        return SortSpec(self._field, -1)

    def in_(self, values: list[Any]) -> In:
        return In(self._field, values)

    def not_in(self, values: list[Any]) -> NotIn:
        return NotIn(self._field, values)

    def exists(self, value: bool = True) -> Exists:
        return Exists(self._field, value)

    def regex(self, pattern: str, options: str | None = None) -> Regex:
        return Regex(self._field, pattern, options)

    def size(self, count: int) -> Size:
        return Size(self._field, count)

    def all_(self, values: list[Any]) -> All:
        return All(self._field, values)

    def elem_match(self, expression: QueryExpression) -> ElemMatch:
        return ElemMatch(self._field, expression)

    def near(
        self,
        coordinates: tuple[float, float],
        max_distance: float | None = None,
        min_distance: float | None = None,
    ) -> Near:
        return Near(self._field, coordinates, max_distance, min_distance)

    def near_sphere(
        self,
        coordinates: tuple[float, float],
        max_distance: float | None = None,
        min_distance: float | None = None,
    ) -> NearSphere:
        return NearSphere(self._field, coordinates, max_distance, min_distance)

    def geo_within(self, geometry: GeoJSONType) -> GeoWithin:
        return GeoWithin(self._field, geometry)

    def geo_intersects(self, geometry: GeoJSONType) -> GeoIntersects:
        return GeoIntersects(self._field, geometry)

    def asc(self) -> SortSpec:
        return SortSpec(self._field, 1)

    def desc(self) -> SortSpec:
        return SortSpec(self._field, -1)

def resolve_agg_refs(value: Any) -> Any:
    if isinstance(value, FieldRef):
        return f"${value._field}"
    if isinstance(value, dict):
        return {k: resolve_agg_refs(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve_agg_refs(v) for v in value]
    return value


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


def near(
    field: MongoFieldPath,
    coordinates: tuple[float, float],
    max_distance: float | None = None,
    min_distance: float | None = None,
) -> Near:
    return Near(field, coordinates, max_distance, min_distance)


def near_sphere(
    field: MongoFieldPath,
    coordinates: tuple[float, float],
    max_distance: float | None = None,
    min_distance: float | None = None,
) -> NearSphere:
    return NearSphere(field, coordinates, max_distance, min_distance)


def geo_within(field: MongoFieldPath, geometry: GeoJSONType) -> GeoWithin:
    return GeoWithin(field, geometry)


def geo_intersects(field: MongoFieldPath, geometry: GeoJSONType) -> GeoIntersects:
    return GeoIntersects(field, geometry)


def text_search(
    search: str,
    language: str | None = None,
    case_sensitive: bool | None = None,
    diacritic_sensitive: bool | None = None,
) -> TextSearch:
    return TextSearch(search, language, case_sensitive, diacritic_sensitive)


class Index:
    def __init__(self, *fields: FieldRef | SortSpec | str, **options: Any) -> None:
        self._keys: list[tuple[str, int]] = []
        for field in fields:
            if isinstance(field, FieldRef):
                self._keys.append((field._field, 1))
            elif isinstance(field, SortSpec):
                self._keys.append((field.field_name, field.direction))
            elif isinstance(field, str):
                self._keys.append((field, 1))
            else:
                raise TypeError(
                    f"Expected FieldRef, SortSpec, or str, got {type(field).__name__}"
                )
        self._options = options

    def to_dict(self) -> dict[str, Any]:
        return {"key": self._keys, **self._options}

    def validate(self, model_cls: type) -> None:
        valid = set(model_cls.model_fields)
        for key, _ in self._keys:
            if key not in valid:
                raise ValueError(
                    f"Unknown field {key!r} in index for {model_cls.__name__}. "
                    f"Valid fields: {sorted(valid)}"
                )

    @classmethod
    def resolve(cls, index: Index | dict[str, Any]) -> dict[str, Any]:
        if isinstance(index, cls):
            return index.to_dict()
        return index
