# Vellum

**The Precision ODM for Asynchronous MongoDB & Pydantic.**

Vellum is a type-safe, async Python ODM for MongoDB built on Pydantic v2 and Motor. It provides a clean repository pattern, fluent aggregation builder, lifecycle hooks, optimistic concurrency, soft deletes, and transactions — all with full type hints.

## Features

| Feature | Description |
|---|---|
| **Type-safe queries** | Expression classes for all MongoDB operators (`Eq`, `Gt`, `In`, `Regex`, `ElemMatch`, Text Search, Geospatial, ...) |
| **Fluent field references** | Write `Product.price < 10` or `Product.fields.price < 10` |
| **Fluent aggregation** | `AggregationPipeline` with `match`, `group`, `project`, `sort`, `unwind`, `lookup`, `add_fields`, `count` |
| **Lifecycle hooks** | `before_insert`, `after_insert`, `before_update`, ... on your model |
| **Optimistic concurrency** | `OptimisticConcurrencyMixin` — automatic version-based conflict detection |
| **Soft delete** | `SoftDeleteMixin` — automatic filtering, `soft_delete()` / `restore()` |
| **Transactions** | `async with repo.transaction() as session:` |
| **FastAPI integration** | `repository_factory` for `Depends` injection |
| **Aggregation output models** | Validate aggregation results with Pydantic models |
| **Migrations** | `MigrationRunner` with up/down, status, rollback |
| **Caching** | `CachedRepository` with configurable TTL and invalidation |
| **Encryption** | `EncryptedField` / `encrypted_field` — Fernet-based field encryption |
| **Schema Doctor** | `SchemaDoctor` — check and repair schema conformance |
| **Seeding** | `Seeder` / `Factory` — generate test data |
| **Change streams** | `ChangeStream` — watch MongoDB change events |
| **Telemetry** | `TracedRepository` — wrap repository with tracing |

## Quick Start

```python
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from vellum import VellumBaseModel, VellumRepository

# 1. Define a model
class Product(VellumBaseModel):
    name: str
    price: float

    class Settings:
        collection_name = "products"

async def main():
    # 2. Connect
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["myapp"]
    repo = VellumRepository(Product, db)

    # 3. Create
    product = Product(name="Widget", price=9.99)
    created = await repo.create(product)
    print(f"Created: {created.id}")

    # 4. Read
    fetched = await repo.get(created.id)
    print(f"Fetched: {fetched.name}")

    # 5. Update
    fetched.price = 24.99
    updated = await repo.update(fetched.id, fetched)

    # 6. Query with field references
    results = await repo.find(
        (Product.price >= 10.0).to_mongo_query()
    )

    # 7. Delete
    await repo.delete(created.id)

    client.close()

asyncio.run(main())
```
