# Advanced Features

## Lifecycle Hooks

Override hook methods on your model to run logic automatically:

```python
class AuditedItem(VellumBaseModel):
    name: str

    async def before_insert(self) -> None:
        print(f"About to insert {self.name}")

    async def after_insert(self) -> None:
        print(f"Inserted {self.name}")

    async def before_update(self) -> None:
        print(f"About to update {self.name}")

    async def after_update(self) -> None:
        print(f"Updated {self.name}")

    async def before_delete(self) -> None:
        print(f"About to delete {self.name}")

    async def after_delete(self) -> None:
        print(f"Deleted {self.name}")
```

Hooks are called automatically by `repo.create()`, `repo.update()`, `repo.delete()`.

To cancel an operation, raise `HookError` in a `before_*` hook:

```python
from vellum import HookError

async def before_insert(self) -> None:
    if not self.name:
        raise HookError("Name is required")
```

## Optimistic Concurrency

Prevent lost updates with version-based conflict detection:

```python
from vellum import OptimisticConcurrencyMixin, OptimisticLockError

class Product(OptimisticConcurrencyMixin, VellumBaseModel):
    name: str
    stock: int

    class Settings:
        collection_name = "products"

p = Product(name="Widget", stock=100)
await repo.create(p)           # version = 1

p.stock = 90
await repo.update(p.id, p)     # version increments to 2

# If another update uses stale version → OptimisticLockError
```

## Soft Delete

Mark documents as deleted without removing them:

```python
from vellum import SoftDeleteMixin

class Post(SoftDeleteMixin, VellumBaseModel):
    title: str

    class Settings:
        collection_name = "posts"
```

### Operations

```python
# Soft delete (sets deleted_at)
await repo.soft_delete(post.id)

# Find excludes soft-deleted by default
results = await repo.find()       # no deleted posts
post = await repo.get(post.id)    # raises DocumentNotFoundError

# Include deleted
results = await repo.find(include_deleted=True)

# Restore
await repo.restore(post.id)
```

### Count

```python
count = await repo.count()  # excludes soft-deleted
```

## Transactions

Requires a MongoDB replica set.

```python
async with repo.transaction() as session:
    account_a.balance -= 100
    account_b.balance += 100
    await repo.update(account_a.id, account_a, session=session)
    await repo.update(account_b.id, account_b, session=session)
    # Auto-commits on success, rolls back on error
```

## Migrations

```python
from vellum import MigrationRunner, SimpleMigration

async def add_field(db):
    await db.users.update_many({}, {"$set": {"role": "user"}})

async def remove_field(db):
    await db.users.update_many({}, {"$unset": {"role": ""}})

migration = SimpleMigration(1, "add role field", add_field, remove_field)

runner = MigrationRunner(db)
applied = await runner.run([migration])
rolled_back = await runner.rollback(1)
status = await runner.get_applied()
```

## Schema Doctor

Check and repair schema conformance:

```python
from vellum import SchemaDoctor

doctor = SchemaDoctor[Product](Product, db)
report = await doctor.check()
print(report.issue_count)  # documents with issues

# Repair
await doctor.repair(dry_run=True)  # preview changes
await doctor.repair()              # apply fixes
```

## FastAPI Integration

```python
from fastapi import FastAPI, Depends
from vellum import repository_factory, get_database

app = FastAPI()

@app.on_event("startup")
async def startup():
    app.state.db = await get_database("mongodb://localhost:27017/myapp")

@app.get("/products/{product_id}")
async def get_product(
    product_id: str,
    repo = Depends(repository_factory(Product)),
):
    return await repo.get(product_id)
```

## Seeding

Generate test data:

```python
from vellum import Seeder, Factory

seeder = Seeder(db)

# With builder function
items = await seeder.seed(
    Product, count=5,
    builder=lambda i: {"name": f"Product {i}", "price": i * 10.0},
)

# With factory
factory = Factory(Product, lambda i: {"name": f"Prod {i}", "price": float(i)})
items = await seeder.seed(Product, count=3, factory=factory)
```

## Change Streams

Watch real-time changes:

```python
from vellum import ChangeStream

stream = ChangeStream(repo.collection)

async for event in stream:
    print(f"Operation: {event.operation_type}")
    print(f"Document: {event.document}")
```

With wildcard handlers:

```python
async def on_insert(event):
    print(f"Inserted: {event.document_key}")

stream = ChangeStream(repo.collection, handlers={"insert": on_insert})
await stream.watch()
```

## Telemetry

Wrap any repository for tracing:

```python
from vellum import TracedRepository

traced = TracedRepository(repo)
# All operations are traced; use with OpenTelemetry or similar
```
