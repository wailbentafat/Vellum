from vellum.aggregation import AggregationPipeline
from vellum.caching import CachedRepository, InMemoryCache
from vellum.changestream import ChangeEvent, ChangeStream
from vellum.connection import connect_to_mongodb, get_database
from vellum.doctor import SchemaDoctor
from vellum.encryption import EncryptedField, encrypted_field
from vellum.exceptions import (
    DocumentNotFoundError,
    HookError,
    OptimisticLockError,
    VellumError,
)
from vellum.migration import Migration, MigrationRunner, SimpleMigration
from vellum.model import OptimisticConcurrencyMixin, SoftDeleteMixin, VellumBaseModel
from vellum.query import (
    All,
    And,
    ElemMatch,
    Eq,
    Exists,
    FieldRef,
    FieldsProxy,
    GeoIntersects,
    GeoWithin,
    Gt,
    Gte,
    In,
    Lt,
    Lte,
    Ne,
    Near,
    NearSphere,
    Nor,
    Not,
    NotIn,
    Or,
    Regex,
    Size,
    SortSpec,
    TextSearch,
    all_,
    elem_match,
    eq,
    exists,
    geo_intersects,
    geo_within,
    gt,
    gte,
    in_,
    lt,
    lte,
    ne,
    near,
    near_sphere,
    not_in,
    regex,
    size,
    text_search,
)
from vellum.querybuilder import QueryBuilder
from vellum.reference import Reference
from vellum.repository import VellumRepository
from vellum.seeder import Factory, Seeder
from vellum.telemetry import TracedRepository
from vellum.update import UpdateBuilder
from vellum.validation import ValidationMixin

__all__ = [
    "VellumBaseModel",
    "VellumRepository",
    "OptimisticConcurrencyMixin",
    "SoftDeleteMixin",
    "AggregationPipeline",
    "FieldRef", "FieldsProxy", "SortSpec",
    "Eq", "Ne", "Gt", "Gte", "Lt", "Lte",
    "Near", "NearSphere", "GeoWithin", "GeoIntersects",
    "TextSearch",
    "In", "NotIn", "All", "Size", "ElemMatch",
    "Exists", "Regex",
    "And", "Or", "Nor", "Not",
    "eq", "ne", "gt", "gte", "lt", "lte",
    "in_", "not_in", "all_", "size", "elem_match",
    "exists", "regex",
    "near", "near_sphere", "geo_within", "geo_intersects",
    "TextSearch", "text_search",
    "VellumError",
    "DocumentNotFoundError",
    "OptimisticLockError",
    "HookError",
    "connect_to_mongodb",
    "get_database",
    "UpdateBuilder",
    "QueryBuilder",
    "SchemaDoctor",
    "ChangeStream", "ChangeEvent",
    "Reference",
    "Migration", "SimpleMigration", "MigrationRunner",
    "CachedRepository", "InMemoryCache",
    "TracedRepository",
    "Factory", "Seeder",
    "ValidationMixin",
    "EncryptedField",
    "encrypted_field",
]
