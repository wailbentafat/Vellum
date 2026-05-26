from __future__ import annotations

import pytest

from vellum import VellumBaseModel, VellumRepository
from vellum.reference import Reference


class Address(VellumBaseModel):
    city: str

    class Settings:
        collection_name = "addresses"


class Person(VellumBaseModel):
    name: str
    address: Reference | None = None

    class Settings:
        collection_name = "persons"


@pytest.fixture
async def addr_repo(db):
    return VellumRepository(Address, db)


@pytest.fixture
async def person_repo(db):
    return VellumRepository(Person, db)


@pytest.mark.asyncio
async def test_reference_round_trip(addr_repo, person_repo):
    addr = await addr_repo.create(Address(city="Paris"))
    person = await person_repo.create(Person(name="Alice", address=addr.id))
    fetched = await person_repo.get(person.id)
    assert fetched.address == addr.id
    assert isinstance(fetched.address, type(addr.id))


@pytest.mark.asyncio
async def test_populate_reference(addr_repo, person_repo):
    addr = await addr_repo.create(Address(city="London"))
    person = await person_repo.create(Person(name="Bob", address=addr.id))
    populated = await person_repo.populate(person, "address", addr_repo)
    assert populated.address.city == "London"


@pytest.mark.asyncio
async def test_populate_none_reference(person_repo, addr_repo):
    person = await person_repo.create(Person(name="Charlie"))
    result = await person_repo.populate(person, "address", addr_repo)
    assert result.address is None


@pytest.mark.asyncio
async def test_populate_many(addr_repo, person_repo):
    cities = ["Tokyo", "Berlin", "Madrid"]
    addrs = [await addr_repo.create(Address(city=c)) for c in cities]
    persons = [
        await person_repo.create(Person(name=f"User{i}", address=a.id))
        for i, a in enumerate(addrs)
    ]
    populated = await person_repo.populate_many(persons, "address", addr_repo)
    assert len(populated) == 3
    assert populated[0].address.city == "Tokyo"
    assert populated[1].address.city == "Berlin"
    assert populated[2].address.city == "Madrid"
