from typing import Callable, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase

from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository

T = TypeVar("T", bound=VellumBaseModel)


def repository_factory(
    model_cls: Type[T],
    get_db: Callable[[], AsyncIOMotorDatabase],
) -> Callable[[], VellumRepository[T]]:
    def _dependency(db: AsyncIOMotorDatabase = get_db()) -> VellumRepository[T]:
        return VellumRepository(model_cls, db)

    return _dependency
