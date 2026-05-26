# Vellum

**The Precision ODM for Asynchronous MongoDB & Pydantic.**

Vellum is a type-safe, async Python ODM for MongoDB built on **Pydantic v2** and **Motor**. It provides a clean repository pattern, fluent aggregation builder, lifecycle hooks, optimistic concurrency, soft deletes, and transactions — all with full type hints.

## Features

- **Type-safe queries** — Expression classes for all MongoDB operators (`Eq`, `Gt`, `In`, `Regex`, `ElemMatch`, `Near`, `TextSearch`, ...) with a field-reference DSL (`User.fields.name == "Alice"`)
- **Fluent aggregation** — `AggregationPipeline` with `match`, `group`, `project`, `sort`, `unwind`, `lookup`, and more; optionally pass an `output_model` for validated results
- **Lifecycle hooks** — Override `before_insert` / `after_insert` / `before_update` / `after_update` / `before_delete` / `after_delete` on your model
- **Optimistic Concurrency Control (OCC)** — `OptimisticConcurrencyMixin` for automatic version-based conflict detection
- **Soft delete** — `SoftDeleteMixin` with automatic filtering of deleted documents
- **Transactions** — `async with repo.transaction() as session:` for multi-document ACID operations
- **FastAPI integration** — `repository_factory` for `Depends`-based dependency injection
- **Bulk operations** — `bulk_create`, `bulk_update`, `bulk_delete` for batch processing
- **Embedded documents** — Full round-trip support for nested Pydantic models
- **Server-side schema validation** — Auto-generate `$jsonSchema` validators from your Pydantic model
- **Aggregation output models** — Pass a Pydantic model to `project()` / `group()` for validated, typed results

## Quick Start

```python
from motor.motor_asyncio import AsyncIOMotorClient
from vellum import VellumBaseModel, VellumRepository


class User(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "users"
        indexes = [{"key": [("email", 1)], "unique": True}]


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    repo = VellumRepository(User, client["myapp"])

    user = await repo.create(User(name="Alice", email="alice@example.com"))
    fetched = await repo.get(user.id)
    print(fetched.name)  # "Alice"

    user.email = "alice@newdomain.com"
    await repo.update(user.id, user)

    users = await repo.find({"name": "Alice"})
    await repo.delete(user.id)
```

## Installation

```bash
pip install vellum
```

Requires Python >= 3.12 and MongoDB >= 4.0. Transactions require a replica set.

## License

MIT
