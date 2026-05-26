from vellum.query import (
    All,
    ElemMatch,
    Eq,
    Exists,
    Gt,
    Gte,
    In,
    Lt,
    Lte,
    Ne,
    Nor,
    Not,
    NotIn,
    Regex,
    Size,
)


def test_eq():
    assert Eq("name", "Alice").to_mongo_query() == {"name": "Alice"}


def test_ne():
    assert Ne("age", 30).to_mongo_query() == {"age": {"$ne": 30}}


def test_gt():
    assert Gt("age", 18).to_mongo_query() == {"age": {"$gt": 18}}


def test_gte():
    assert Gte("age", 18).to_mongo_query() == {"age": {"$gte": 18}}


def test_lt():
    assert Lt("age", 65).to_mongo_query() == {"age": {"$lt": 65}}


def test_lte():
    assert Lte("age", 65).to_mongo_query() == {"age": {"$lte": 65}}


def test_in():
    result = In("status", ["active", "pending"]).to_mongo_query()
    assert result == {"status": {"$in": ["active", "pending"]}}


def test_not_in():
    result = NotIn("status", ["deleted"]).to_mongo_query()
    assert result == {"status": {"$nin": ["deleted"]}}


def test_exists_true():
    assert Exists("email", True).to_mongo_query() == {"email": {"$exists": True}}


def test_exists_false():
    assert Exists("email", False).to_mongo_query() == {"email": {"$exists": False}}


def test_regex():
    result = Regex("name", "^Ali").to_mongo_query()
    assert result == {"name": {"$regex": "^Ali"}}


def test_regex_with_options():
    result = Regex("name", "^ali", options="i").to_mongo_query()
    assert result == {"name": {"$regex": "^ali", "$options": "i"}}


def test_size():
    assert Size("tags", 3).to_mongo_query() == {"tags": {"$size": 3}}


def test_all():
    result = All("tags", ["python", "mongodb"]).to_mongo_query()
    assert result == {"tags": {"$all": ["python", "mongodb"]}}


def test_elem_match():
    inner = Gt("score", 90)
    result = ElemMatch("grades", inner).to_mongo_query()
    assert result == {"grades": {"$elemMatch": {"score": {"$gt": 90}}}}


def test_and_operator():
    expr = Eq("name", "Alice") & Gt("age", 18)
    assert expr.to_mongo_query() == {
        "$and": [{"name": "Alice"}, {"age": {"$gt": 18}}]
    }


def test_or_operator():
    expr = Eq("status", "active") | Eq("status", "pending")
    assert expr.to_mongo_query() == {
        "$or": [{"status": "active"}, {"status": "pending"}]
    }


def test_not_operator():
    expr = Not(Gt("age", 65))
    assert expr.to_mongo_query() == {"$nor": [{"age": {"$gt": 65}}]}


def test_nor():
    expr = Nor(Eq("status", "deleted"), Eq("status", "banned"))
    assert expr.to_mongo_query() == {
        "$nor": [{"status": "deleted"}, {"status": "banned"}]
    }


def test_in_requires_iterable():
    import pytest
    with pytest.raises(TypeError):
        In("field", "not_a_list").to_mongo_query()
