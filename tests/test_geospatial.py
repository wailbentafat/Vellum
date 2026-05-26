from pydantic import Field
import pytest

from vellum.model import VellumBaseModel
from vellum.query import GeoIntersects, GeoWithin, Near, NearSphere


class Place(VellumBaseModel):
    name: str
    location: dict = Field(default_factory=dict)

    class Settings:
        collection_name = "places"


def test_near_query():
    expr = Place.fields.location.near((-73.97, 40.77), max_distance=1000)
    assert isinstance(expr, Near)
    mongo = expr.to_mongo_query()
    assert "$near" in mongo["location"]
    assert mongo["location"]["$near"]["$geometry"]["coordinates"] == [-73.97, 40.77]
    assert mongo["location"]["$near"]["$maxDistance"] == 1000


def test_near_with_min_distance():
    expr = Place.fields.location.near((-73.97, 40.77), min_distance=100)
    mongo = expr.to_mongo_query()
    assert mongo["location"]["$near"]["$minDistance"] == 100


def test_near_sphere():
    expr = Place.fields.location.near_sphere((-73.97, 40.77), max_distance=500)
    assert isinstance(expr, NearSphere)
    mongo = expr.to_mongo_query()
    assert "$nearSphere" in mongo["location"]


def test_geo_within():
    polygon = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
    }
    expr = Place.fields.location.geo_within(polygon)
    assert isinstance(expr, GeoWithin)
    mongo = expr.to_mongo_query()
    assert "$geoWithin" in mongo["location"]
    assert mongo["location"]["$geoWithin"]["$geometry"] == polygon


def test_geo_intersects():
    line = {
        "type": "LineString",
        "coordinates": [[0, 0], [10, 10]],
    }
    expr = Place.fields.location.geo_intersects(line)
    assert isinstance(expr, GeoIntersects)
    mongo = expr.to_mongo_query()
    assert "$geoIntersects" in mongo["location"]
    assert mongo["location"]["$geoIntersects"]["$geometry"] == line


@pytest.mark.asyncio
async def test_near_integration(db):
    from vellum.repository import VellumRepository

    repo = VellumRepository(Place, db)
    await repo.ensure_indexes()
    await repo.collection.create_index([("location", "2dsphere")])

    await repo.create(
        Place(name="NYC", location={"type": "Point", "coordinates": [-74.006, 40.7128]})
    )
    await repo.create(
        Place(name="LA", location={"type": "Point", "coordinates": [-118.2437, 34.0522]})
    )
    await repo.create(
        Place(name="Chicago", location={"type": "Point", "coordinates": [-87.6298, 41.8781]})
    )

    expr = Place.fields.location.near((-74.006, 40.7128), max_distance=5000)
    results = await repo.find(expr.to_mongo_query())
    assert len(results) >= 1
    names = [r.name for r in results]
    assert "NYC" in names
