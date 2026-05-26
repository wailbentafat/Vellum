import pytest
import pytest_asyncio
from pydantic import BaseModel
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository
from vellum.aggregation import AggregationPipeline


class Sale(VellumBaseModel):
    product: str
    quantity: int
    price: float

    class Settings:
        collection_name = "sales"


class SaleSummary(BaseModel):
    product: str
    total_qty: int


@pytest_asyncio.fixture
async def sale_repo(db):
    repo = VellumRepository(Sale, db)
    await repo.create(Sale(product="Apple", quantity=10, price=1.5))
    await repo.create(Sale(product="Apple", quantity=5, price=1.5))
    await repo.create(Sale(product="Banana", quantity=20, price=0.75))
    return repo


@pytest.mark.asyncio
async def test_pipeline_match(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.match({"product": "Apple"}).execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_sort_limit(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.sort([("quantity", -1)]).limit(1).execute()
    assert len(results) == 1
    assert results[0]["quantity"] == 20


@pytest.mark.asyncio
async def test_pipeline_skip(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.sort([("quantity", 1)]).skip(1).execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_project(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.project({"product": 1, "_id": 0}).execute()
    assert all("product" in r for r in results)
    assert all("price" not in r for r in results)


@pytest.mark.asyncio
async def test_pipeline_group(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await (
        pipeline
        .group("$product", total_qty={"$sum": "$quantity"})
        .execute()
    )
    products = {r["_id"] for r in results}
    assert "Apple" in products
    assert "Banana" in products


@pytest.mark.asyncio
async def test_pipeline_with_output_model(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection, output_model=SaleSummary)
    results = await (
        pipeline
        .group("$product", total_qty={"$sum": "$quantity"})
        .project({"product": "$_id", "total_qty": 1, "_id": 0}, output_model=SaleSummary)
        .execute()
    )
    assert all(isinstance(r, SaleSummary) for r in results)


@pytest.mark.asyncio
async def test_pipeline_unwind(sale_repo):
    from motor.motor_asyncio import AsyncIOMotorCollection
    col: AsyncIOMotorCollection = sale_repo.collection
    await col.insert_one({"tags": ["fresh", "organic"], "product": "Apple", "quantity": 1, "price": 2.0, "_id": "test-unwind"})

    pipeline = AggregationPipeline(col)
    results = await pipeline.match({"_id": "test-unwind"}).unwind("$tags").execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_add_fields(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.add_fields({"revenue": {"$multiply": ["$price", "$quantity"]}}).execute()
    assert all("revenue" in r for r in results)


@pytest.mark.asyncio
async def test_pipeline_count_stage(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.count_stage("total").execute()
    assert len(results) == 1
    assert results[0]["total"] == 3
