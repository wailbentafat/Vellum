import datetime
from typing import Any, ClassVar, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic._internal._model_construction import ModelMetaclass

from vellum.hooks import HooksMixin
from vellum.query import FieldRef, FieldsProxy, Index


class OptimisticConcurrencyMixin(BaseModel):
    version: int = 1


class SoftDeleteMixin(BaseModel):
    deleted_at: datetime.datetime | None = None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

T = TypeVar("T", bound="VellumBaseModel")


class VellumMetaclass(ModelMetaclass):
    def __getattr__(cls, name: str) -> Any:  # noqa: N805
        if name.startswith("_"):
            raise AttributeError(name)
        fields = cls.__dict__.get("__pydantic_fields__", {})
        if name in fields:
            return FieldRef(name)
        raise AttributeError(
            f"{cls.__name__} has no attribute {name!r}"
        )

    def __init__(cls, name: str, bases: tuple, namespace: dict, **kwargs: Any) -> None:  # noqa: N805
        super().__init__(name, bases, namespace, **kwargs)
        init_indexes = cls.__init_indexes__()
        if init_indexes:
            current = getattr(cls.Settings, "indexes", [])
            cls.Settings.indexes = [*current, *init_indexes]


class VellumBaseModel(HooksMixin, BaseModel, metaclass=VellumMetaclass):

    id: UUID = Field(default_factory=uuid4, alias="_id")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.fields: FieldsProxy = FieldsProxy(cls)

    @classmethod
    def __init_indexes__(cls) -> list[Index | dict[str, Any]]:
        return []

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        from_attributes=True,
        protected_namespaces=(),
    )

    class Settings:
        collection_name: ClassVar[str | None] = None
        indexes: ClassVar[list[Index | dict[str, Any]]] = []

    @classmethod
    def get_collection_name(cls) -> str:
        name = cls.Settings.collection_name
        return name if name else cls.__name__.lower()

    def to_mongo(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=False)
        if "_id" in data and isinstance(data["_id"], UUID):
            data["_id"] = str(data["_id"])
        return data

    @classmethod
    def from_mongo(cls: type[T], data: dict[str, Any]) -> T:
        if "_id" in data and isinstance(data["_id"], str):
            data["_id"] = UUID(data["_id"])
        return cls.model_validate(data)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("created_at", "updated_at", "id") or name.startswith("model_"):
            super().__setattr__(name, value)
            return
        current = self.__dict__.get(name)
        if current is not None and current != value:
            super().__setattr__(
                "updated_at", datetime.datetime.now(datetime.UTC)
            )
        super().__setattr__(name, value)
