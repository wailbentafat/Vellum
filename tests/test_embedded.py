from pydantic import BaseModel
import pytest

from vellum.model import VellumBaseModel
from vellum.query import Eq


class Address(BaseModel):
    city: str
    state: str
    zip: str


class Person(VellumBaseModel):
    name: str
    address: Address

    class Settings:
        collection_name = "persons"


def test_field_ref_nested_attribute():
    expr = Person.fields.address.city == "NYC"
    assert isinstance(expr, Eq)
    assert expr.to_mongo_query() == {"address.city": "NYC"}


def test_field_ref_nested_chain():
    expr = Person.fields.address.state != "CA"
    assert expr.to_mongo_query() == {"address.state": {"$ne": "CA"}}


def test_field_ref_hash():
    ref = Person.fields.address.city
    assert hash(ref) == hash("address.city")
    assert isinstance(ref, Person.fields.address.__class__)


@pytest.mark.asyncio
async def test_embedded_round_trip(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Person, db)

    person = Person(
        name="Alice",
        address=Address(city="NYC", state="NY", zip="10001"),
    )
    created = await repo.create(person)
    assert created.address.city == "NYC"
    assert created.address.state == "NY"

    fetched = await repo.get(created.id)
    assert isinstance(fetched.address, Address)
    assert fetched.address.city == "NYC"
    assert fetched.address.zip == "10001"


@pytest.mark.asyncio
async def test_query_by_embedded_field(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Person, db)

    await repo.create(Person(name="Alice", address=Address(city="NYC", state="NY", zip="10001")))
    await repo.create(Person(name="Bob", address=Address(city="LA", state="CA", zip="90001")))
    await repo.create(Person(name="Charlie", address=Address(city="NYC", state="NY", zip="10002")))

    expr = Person.fields.address.city == "NYC"
    results = await repo.find(expr.to_mongo_query())
    assert len(results) == 2

    expr2 = Person.fields.address.state == "CA"
    results2 = await repo.find(expr2.to_mongo_query())
    assert len(results2) == 1
    assert results2[0].name == "Bob"


@pytest.mark.asyncio
async def test_embedded_update(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Person, db)

    person = await repo.create(
        Person(name="Dave", address=Address(city="Boston", state="MA", zip="02101"))
    )
    person.address.city = "Cambridge"
    await repo.update(person.id, person)

    fetched = await repo.get(person.id)
    assert fetched.address.city == "Cambridge"
    assert fetched.address.state == "MA"


def test_to_mongo_serializes_embedded():
    person = Person(
        name="Test",
        address=Address(city="Chicago", state="IL", zip="60601"),
    )
    mongo = person.to_mongo()
    assert mongo["address"] == {"city": "Chicago", "state": "IL", "zip": "60601"}
    assert "_id" in mongo


def test_from_mongo_deserializes_embedded():
    raw = {
        "_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Test",
        "address": {"city": "Chicago", "state": "IL", "zip": "60601"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    person = Person.from_mongo(raw)
    assert isinstance(person.address, Address)
    assert person.address.city == "Chicago"
