from __future__ import annotations

import pytest

from vellum import (
    All,
    And,
    Eq,
    Gt,
    Gte,
    In,
    Index,
    Lt,
    Lte,
    Ne,
    NotIn,
    Regex,
    Size,
    SortSpec,
    VellumBaseModel,
    resolve_agg_refs,
)


class Item(VellumBaseModel):
    name: str
    price: float
    quantity: int = 0
    tags: list[str] = []
    in_stock: bool = True

    class Settings:
        collection_name = "items"

    @classmethod
    def __init_indexes__(cls):
        return [
            Index(cls.name),
            Index(cls.price),
            Index(cls.name, cls.price),
            Index(cls.tags),
        ]


class TestExamplePatterns:
    def test_direct_field_ref_queries(self):
        assert (Item.name == "Widget").to_mongo_query() == {"name": "Widget"}
        assert (Item.price > 10).to_mongo_query() == {"price": {"$gt": 10}}
        assert (Item.price >= 10).to_mongo_query() == {"price": {"$gte": 10}}
        assert (Item.price < 20).to_mongo_query() == {"price": {"$lt": 20}}
        assert (Item.price <= 20).to_mongo_query() == {"price": {"$lte": 20}}
        assert (Item.price != 10).to_mongo_query() == {"price": {"$ne": 10}}

    def test_composed_queries(self):
        q = ((Item.name == "Widget") & (Item.price > 100)).to_mongo_query()
        assert q == {
            "$and": [{"name": "Widget"}, {"price": {"$gt": 100}}]
        }

        q = ((Item.name == "A") | (Item.name == "B")).to_mongo_query()
        assert q == {"$or": [{"name": "A"}, {"name": "B"}]}

    def test_array_operators(self):
        assert Item.tags.in_(["a", "b"]).to_mongo_query() == {"tags": {"$in": ["a", "b"]}}
        assert Item.tags.all_(["a", "b"]).to_mongo_query() == {"tags": {"$all": ["a", "b"]}}
        assert Item.tags.size(3).to_mongo_query() == {"tags": {"$size": 3}}

    def test_regex_query(self):
        assert Item.name.regex("^Widget").to_mongo_query() == {"name": {"$regex": "^Widget"}}

    def test_field_ref_sorting(self):
        assert Item.price.asc() == SortSpec("price", 1)
        assert Item.price.desc() == SortSpec("price", -1)
        assert (+Item.price) == SortSpec("price", 1)
        assert (-Item.price) == SortSpec("price", -1)

    def test_agg_refs(self):
        assert resolve_agg_refs(Item.price) == "$price"
        assert resolve_agg_refs({"$sum": Item.price}) == {"$sum": "$price"}
        assert resolve_agg_refs([Item.price, Item.name]) == ["$price", "$name"]
        assert resolve_agg_refs(
            {"$multiply": [Item.price, Item.quantity]}
        ) == {"$multiply": ["$price", "$quantity"]}

    def test_index_syntax(self):
        idx = Index(Item.name)
        assert idx.to_dict() == {"key": [("name", 1)]}

        idx = Index(Item.name, Item.price)
        assert idx.to_dict() == {"key": [("name", 1), ("price", 1)]}

        idx = Index(Item.name, unique=True)
        assert idx.to_dict() == {"key": [("name", 1)], "unique": True}

    def test_init_indexes_classmethod(self):
        assert len(Item.Settings.indexes) == 4


class TestExampleModels:
    def test_model_creation(self):
        item = Item(name="Widget", price=9.99, tags=["new"])
        assert item.name == "Widget"
        assert item.price == 9.99
        assert item.tags == ["new"]
        assert item.in_stock is True

    def test_model_serialization(self):
        item = Item(name="Test", price=1.99)
        doc = item.to_mongo()
        assert doc["name"] == "Test"
        assert doc["price"] == 1.99
        assert "_id" in doc

    def test_model_deserialization(self):
        from uuid import uuid4
        item_id = uuid4()
        doc = {"_id": str(item_id), "name": "Test", "price": 1.99, "tags": [], "in_stock": True}
        item = Item.from_mongo(doc)
        assert item.id == item_id
        assert item.name == "Test"
        assert item.price == 1.99

    def test_example_imports_work(self):
        from examples.ecommerce import Category, Order, Product
        assert issubclass(Category, VellumBaseModel)
        assert issubclass(Product, VellumBaseModel)
        assert issubclass(Order, VellumBaseModel)
