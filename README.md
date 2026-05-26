# Vellum

**The Precision ODM for Asynchronous MongoDB & Pydantic.**

Vellum is a type-safe, async Python ODM for MongoDB built on Pydantic v2 and Motor. It provides a clean repository pattern, fluent aggregation builder, lifecycle hooks, optimistic concurrency, soft deletes, and transactions — all with full type hints.

## Installation

```bash
pip install vellum-odm
```

## Quick Start

```python
from motor.motor_asyncio import AsyncIOMotorClient
from vellum import VellumBaseModel, VellumRepository, AggregationPipeline

# 1. Define a model
class User(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "users"
        indexes = [{"key": [("email", 1)], "unique": True}]

# 2. Connect and create a repository
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["myapp"]
repo = VellumRepository(User, db)

# 3. CRUD
user = await repo.create(User(name="Alice", email="alice@example.com"))
fetched = await repo.get(user.id)
user.name = "Bob"
await repo.update(user.id, user)
await repo.delete(user.id)

# 4. Query
users = await repo.find({"name": "Alice"})
count = await repo.count({"name": "Alice"})

# 5. Aggregation
results = await (
    AggregationPipeline(repo.collection)
    .match({"status": "active"})
    .group("$department", total={"$sum": 1})
    .sort([("total", -1)])
    .execute()
)
```

## Features

| Feature | Description |
|---|---|
| **Type-safe queries** | Expression classes for all MongoDB operators (`Eq`, `Gt`, `In`, `Regex`, `ElemMatch`, ...) |
| **Fluent aggregation** | `AggregationPipeline` with `match`, `group`, `project`, `sort`, `unwind`, `lookup`, etc. |
| **Lifecycle hooks** | `before_insert`, `after_insert`, `before_update`, ... on your model |
| **OCC** | `OptimisticConcurrencyMixin` — automatic version-based conflict detection |
| **Soft delete** | `SoftDeleteMixin` — automatic filtering, `soft_delete()` / `restore()` |
| **Transactions** | `async with repo.transaction() as session:` |
| **FastAPI integration** | `repository_factory` for `Depends` injection |
| **Aggregation output models** | Pass a Pydantic model to `project()` / `group()` for validated results |

## Documentation

- [Learning Guide](docs/learning.md) — explains bugs found and concepts introduced
- [Roadmap](docs/roadmap.md) — planned features and improvements

## Requirements

- Python >= 3.12
- MongoDB >= 4.0 (transactions require a replica set)

## License

MIT
