import datetime
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from vellum.hooks import HooksMixin


class OptimisticConcurrencyMixin(BaseModel):
    version: int = 1

T = TypeVar("T", bound="VellumBaseModel")


class VellumBaseModel(HooksMixin, BaseModel):

    id: UUID = Field(default_factory=uuid4, alias="_id")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        from_attributes=True,
        protected_namespaces=(),
    )

    class Settings:
        collection_name: ClassVar[Optional[str]] = None

    @classmethod
    def get_collection_name(cls) -> str:
        name = cls.Settings.collection_name
        return name if name else cls.__name__.lower()

    def to_mongo(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True, exclude_none=False)
        if "_id" in data and isinstance(data["_id"], UUID):
            data["_id"] = str(data["_id"])
        return data

    @classmethod
    def from_mongo(cls: Type[T], data: Dict[str, Any]) -> T:
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
                "updated_at", datetime.datetime.now(datetime.timezone.utc)
            )
        super().__setattr__(name, value)
