import pytest

from vellum.query import TextSearch, text_search


def test_text_search_basic():
    expr = TextSearch("coffee")
    assert expr.to_mongo_query() == {"$text": {"$search": "coffee"}}


def test_text_search_with_language():
    expr = TextSearch("café", language="fr")
    mongo = expr.to_mongo_query()
    assert mongo["$text"]["$search"] == "café"
    assert mongo["$text"]["$language"] == "fr"


def test_text_search_case_sensitive():
    expr = TextSearch("Coffee", case_sensitive=True)
    mongo = expr.to_mongo_query()
    assert mongo["$text"]["$caseSensitive"] is True


def test_text_search_diacritic_sensitive():
    expr = TextSearch("cafe", diacritic_sensitive=True)
    mongo = expr.to_mongo_query()
    assert mongo["$text"]["$diacriticSensitive"] is True


def test_text_search_all_options():
    expr = TextSearch("coffee", language="en", case_sensitive=True, diacritic_sensitive=False)
    mongo = expr.to_mongo_query()
    assert mongo["$text"]["$search"] == "coffee"
    assert mongo["$text"]["$language"] == "en"
    assert mongo["$text"]["$caseSensitive"] is True
    assert mongo["$text"]["$diacriticSensitive"] is False


def test_text_search_function():
    expr = text_search("coffee", language="en")
    assert isinstance(expr, TextSearch)
    assert expr.to_mongo_query() == {"$text": {"$search": "coffee", "$language": "en"}}


def test_text_search_cannot_be_composed():
    expr = TextSearch("coffee")
    with pytest.raises(TypeError):
        _ = expr & TextSearch("tea")
    with pytest.raises(TypeError):
        _ = expr | TextSearch("tea")
    with pytest.raises(TypeError):
        _ = ~expr


@pytest.mark.asyncio
async def test_text_search_integration(db):
    from vellum.model import VellumBaseModel
    from vellum.repository import VellumRepository

    class Article(VellumBaseModel):
        title: str
        content: str

        class Settings:
            collection_name = "articles"

    repo = VellumRepository(Article, db)
    await repo.collection.create_index([("title", "text"), ("content", "text")])

    await repo.create(Article(title="Coffee Brewing", content="How to brew perfect coffee"))
    await repo.create(Article(title="Tea Time", content="All about tea"))
    await repo.create(Article(title="Espresso", content="Strong coffee drink"))

    expr = text_search("coffee")
    results = await repo.find(expr.to_mongo_query())
    assert len(results) >= 2
