import pytest

from vellum.model import VellumBaseModel
from vellum.query import All, And, ElemMatch, Eq, Gt, Gte, In, Lt, Lte, Ne, Not, NotIn, Or, Size


class Item(VellumBaseModel):
    name: str
    price: float
    tags: list[str] = []

    class Settings:
        collection_name = "items"


def test_eq():
    expr = Item.fields.name == "Widget"
    assert isinstance(expr, Eq)
    assert expr.to_mongo_query() == {"name": "Widget"}


def test_ne():
    expr = Item.fields.name != "Widget"
    assert isinstance(expr, Ne)
    assert expr.to_mongo_query() == {"name": {"$ne": "Widget"}}


def test_gt():
    expr = Item.fields.price > 10.0
    assert isinstance(expr, Gt)
    assert expr.to_mongo_query() == {"price": {"$gt": 10.0}}


def test_gte():
    expr = Item.fields.price >= 10.0
    assert isinstance(expr, Gte)
    assert expr.to_mongo_query() == {"price": {"$gte": 10.0}}


def test_lt():
    expr = Item.fields.price < 20.0
    assert isinstance(expr, Lt)
    assert expr.to_mongo_query() == {"price": {"$lt": 20.0}}


def test_lte():
    expr = Item.fields.price <= 20.0
    assert isinstance(expr, Lte)
    assert expr.to_mongo_query() == {"price": {"$lte": 20.0}}


def test_in():
    expr = Item.fields.name.in_(["A", "B"])
    assert isinstance(expr, In)
    assert expr.to_mongo_query() == {"name": {"$in": ["A", "B"]}}


def test_not_in():
    expr = Item.fields.name.not_in(["A", "B"])
    assert isinstance(expr, NotIn)
    assert expr.to_mongo_query() == {"name": {"$nin": ["A", "B"]}}


def test_exists():
    expr = Item.fields.name.exists()
    assert expr.to_mongo_query() == {"name": {"$exists": True}}


def test_regex():
    expr = Item.fields.name.regex("^Widget")
    assert expr.to_mongo_query() == {"name": {"$regex": "^Widget"}}


def test_regex_with_options():
    expr = Item.fields.name.regex("^widget", options="i")
    assert expr.to_mongo_query() == {"name": {"$regex": "^widget", "$options": "i"}}


def test_size():
    expr = Item.fields.tags.size(3)
    assert isinstance(expr, Size)
    assert expr.to_mongo_query() == {"tags": {"$size": 3}}


def test_all():
    expr = Item.fields.tags.all_(["a", "b"])
    assert isinstance(expr, All)
    assert expr.to_mongo_query() == {"tags": {"$all": ["a", "b"]}}


def test_elem_match():
    inner = Item.fields.price > 5.0
    expr = Item.fields.tags.elem_match(inner)
    assert isinstance(expr, ElemMatch)
    assert expr.to_mongo_query() == {"tags": {"$elemMatch": {"price": {"$gt": 5.0}}}}


def test_compose_and():
    expr = (Item.fields.name == "Widget") & (Item.fields.price > 10.0)
    assert isinstance(expr, And)
    mongo = expr.to_mongo_query()
    assert "$and" in mongo
    assert len(mongo["$and"]) == 2


def test_compose_or():
    expr = (Item.fields.name == "A") | (Item.fields.name == "B")
    assert isinstance(expr, Or)
    mongo = expr.to_mongo_query()
    assert "$or" in mongo
    assert len(mongo["$or"]) == 2


def test_invert():
    expr = ~(Item.fields.name == "Widget")
    assert isinstance(expr, Not)
    assert expr.to_mongo_query() == {"$nor": [{"name": "Widget"}]}


# --- Direct field reference syntax (Beanie-style) tests ---


def test_direct_ref_eq():
    expr = Item.name == "Widget"
    assert isinstance(expr, Eq)
    assert expr.to_mongo_query() == {"name": "Widget"}


def test_direct_ref_ne():
    expr = Item.name != "Widget"
    assert isinstance(expr, Ne)
    assert expr.to_mongo_query() == {"name": {"$ne": "Widget"}}


def test_direct_ref_gt():
    expr = Item.price > 10.0
    assert isinstance(expr, Gt)
    assert expr.to_mongo_query() == {"price": {"$gt": 10.0}}


def test_direct_ref_gte():
    expr = Item.price >= 10.0
    assert isinstance(expr, Gte)
    assert expr.to_mongo_query() == {"price": {"$gte": 10.0}}


def test_direct_ref_lt():
    expr = Item.price < 20.0
    assert isinstance(expr, Lt)
    assert expr.to_mongo_query() == {"price": {"$lt": 20.0}}


def test_direct_ref_lte():
    expr = Item.price <= 20.0
    assert isinstance(expr, Lte)
    assert expr.to_mongo_query() == {"price": {"$lte": 20.0}}


def test_direct_ref_in():
    expr = Item.name.in_(["A", "B"])
    assert isinstance(expr, In)
    assert expr.to_mongo_query() == {"name": {"$in": ["A", "B"]}}


def test_direct_ref_not_in():
    expr = Item.name.not_in(["A", "B"])
    assert isinstance(expr, NotIn)
    assert expr.to_mongo_query() == {"name": {"$nin": ["A", "B"]}}


def test_direct_ref_exists():
    expr = Item.name.exists()
    assert expr.to_mongo_query() == {"name": {"$exists": True}}


def test_direct_ref_regex():
    expr = Item.name.regex("^Widget")
    assert expr.to_mongo_query() == {"name": {"$regex": "^Widget"}}


def test_direct_ref_size():
    expr = Item.tags.size(3)
    assert isinstance(expr, Size)
    assert expr.to_mongo_query() == {"tags": {"$size": 3}}


def test_direct_ref_all():
    expr = Item.tags.all_(["a", "b"])
    assert isinstance(expr, All)
    assert expr.to_mongo_query() == {"tags": {"$all": ["a", "b"]}}


def test_direct_ref_elem_match():
    inner = Item.price > 5.0
    expr = Item.tags.elem_match(inner)
    assert isinstance(expr, ElemMatch)
    assert expr.to_mongo_query() == {"tags": {"$elemMatch": {"price": {"$gt": 5.0}}}}


def test_direct_ref_compose_and():
    expr = (Item.name == "Widget") & (Item.price > 10.0)
    assert isinstance(expr, And)
    mongo = expr.to_mongo_query()
    assert "$and" in mongo
    assert len(mongo["$and"]) == 2


def test_direct_ref_compose_or():
    expr = (Item.name == "A") | (Item.name == "B")
    assert isinstance(expr, Or)
    mongo = expr.to_mongo_query()
    assert "$or" in mongo
    assert len(mongo["$or"]) == 2


def test_direct_ref_invert():
    expr = ~(Item.name == "Widget")
    assert isinstance(expr, Not)
    assert expr.to_mongo_query() == {"$nor": [{"name": "Widget"}]}


def test_direct_ref_sort_asc():
    spec = +Item.price
    assert spec.field_name == "price"
    assert spec.direction == 1


def test_direct_ref_sort_desc():
    spec = -Item.price
    assert spec.field_name == "price"
    assert spec.direction == -1


def test_direct_ref_id_field():
    from uuid import UUID

    expr = Item.id == UUID("00000000-0000-0000-0000-000000000001")
    assert isinstance(expr, Eq)
    q = expr.to_mongo_query()
    assert "id" in q
    assert q["id"] == "00000000-0000-0000-0000-000000000001"


# --- Backward compat: .fields proxy still works ---

def test_field_not_found():
    try:
        Item.fields.nonexistent
        assert False, "Expected AttributeError"
    except AttributeError:
        pass


def test_fields_proxy_still_works():
    expr = Item.fields.name == "Widget"
    assert isinstance(expr, Eq)
    assert expr.to_mongo_query() == {"name": "Widget"}


@pytest.mark.asyncio
async def test_integration_with_repository(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Item, db)
    await repo.create(Item(name="Cheap", price=5.0))
    await repo.create(Item(name="Mid", price=15.0))
    await repo.create(Item(name="Pricey", price=50.0))

    expr = (Item.fields.price >= 10.0) & (Item.fields.price <= 30.0)
    results = await repo.find(expr.to_mongo_query())
    assert len(results) == 1
    assert results[0].name == "Mid"


@pytest.mark.asyncio
async def test_direct_ref_integration_with_repository(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Item, db)
    await repo.create(Item(name="Alpha", price=5.0))
    await repo.create(Item(name="Beta", price=15.0))

    expr = (Item.price >= 10.0) & (Item.price <= 30.0)
    results = await repo.find(expr.to_mongo_query())
    assert len(results) == 1
    assert results[0].name == "Beta"
