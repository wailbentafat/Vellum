import datetime
from uuid import UUID
from vellum.model import VellumBaseModel


class User(VellumBaseModel):
    name: str
    age: int

    class Settings:
        collection_name = "users"


def test_model_has_uuid_id():
    user = User(name="Alice", age=30)
    assert isinstance(user.id, UUID)


def test_model_has_timestamps():
    user = User(name="Alice", age=30)
    assert isinstance(user.created_at, datetime.datetime)
    assert isinstance(user.updated_at, datetime.datetime)
    assert user.created_at.tzinfo is not None


def test_get_collection_name_from_settings():
    assert User.get_collection_name() == "users"


def test_get_collection_name_fallback():
    class Product(VellumBaseModel):
        title: str

    assert Product.get_collection_name() == "product"


def test_to_mongo_stores_id_as_string():
    user = User(name="Alice", age=30)
    doc = user.to_mongo()
    assert doc["_id"] == str(user.id)
    assert "id" not in doc


def test_from_mongo_restores_model():
    user = User(name="Alice", age=30)
    doc = user.to_mongo()
    restored = User.from_mongo(doc)
    assert restored.id == user.id
    assert restored.name == "Alice"


def test_setattr_updates_updated_at():
    user = User(name="Alice", age=30)
    old_updated = user.updated_at
    user.name = "Bob"
    assert user.updated_at >= old_updated
    assert user.name == "Bob"


def test_settings_default_collection_name():
    class Order(VellumBaseModel):
        total: float

    assert Order.get_collection_name() == "order"
