from collections.abc import Callable

from motor.motor_asyncio import AsyncIOMotorDatabase

from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


def repository_factory[T: VellumBaseModel](
    model_cls: type[T],
    get_db: Callable[[], AsyncIOMotorDatabase],
) -> Callable[[], VellumRepository[T]]:
    def _dependency(db: AsyncIOMotorDatabase = get_db()) -> VellumRepository[T]:
        return VellumRepository(model_cls, db)

    return _dependency
