# Repository

The repository pattern provides a clean abstraction over MongoDB collection operations.

## Setup

```python
from motor.motor_asyncio import AsyncIOMotorClient
from vellum import VellumBaseModel, VellumRepository

class Product(VellumBaseModel):
    name: str
    price: float

    class Settings:
        collection_name = "products"

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["myapp"]
repo = VellumRepository(Product, db)
```

## Create

```python
product = Product(name="Widget", price=9.99)
created = await repo.create(product)
```

## Read

```python
# By ID
fetched = await repo.get(product.id)

# Get raises DocumentNotFoundError if missing
from vellum import DocumentNotFoundError
try:
    await repo.get(uuid4())
except DocumentNotFoundError:
    pass
```

## Update

```python
product.price = 24.99
updated = await repo.update(product.id, product)
```

## Delete

```python
deleted = await repo.delete(product.id)  # returns True
# Raises DocumentNotFoundError if not found
```

## Find

```python
# All documents
all_products = await repo.find()

# With filter dict
cheap = await repo.find({"price": {"$lt": 20.0}})

# With sort
results = await repo.find(sort=[+Product.price])

# With pagination
results = await repo.find(skip=10, limit=20)
```

## Find One

```python
product = await repo.find_one({"name": "Widget"})
# Returns None if not found
```

## Find or Create

```python
# Returns existing or creates new
product = await repo.find_or_create(
    {"name": "Widget"},
    defaults={"price": 9.99},
)
```

## Upsert

```python
# Replaces document if exists, inserts if not
product = await repo.upsert(
    {"name": "Widget"},
    Product(name="Widget", price=19.99),
)
```

## Count

```python
total = await repo.count()
filtered = await repo.count({"price": {"$gt": 10.0}})
```

## Bulk Operations

```python
# Bulk create
products = [Product(name=f"Item {i}", price=i * 10) for i in range(5)]
await repo.bulk_create(products)

# Bulk update (matching filter)
await repo.bulk_update({"price": {"$lt": 20}}, {"$set": {"price": 20}})

# Bulk delete (matching filter)
await repo.bulk_delete({"price": 0})
```

## Indexes

```python
# Create index
await repo.create_index([("email", 1)], unique=True)

# List indexes
indexes = await repo.list_indexes()

# Drop index
await repo.drop_index("email_1")

# Ensure indexes defined in Settings
await repo.ensure_indexes()
```

## Transactions

Requires a MongoDB replica set.

```python
async with repo.transaction() as session:
    await repo.create(product, session=session)
    await repo.update(product.id, product, session=session)
```

## Cached Repository

Wraps any repository with an in-memory cache:

```python
from vellum import CachedRepository

cached_repo = CachedRepository(repo, ttl=300)  # 5 minute TTL

# First call hits DB, second returns cached
await cached_repo.get(product.id)
await cached_repo.get(product.id)  # from cache

# Invalidate
cached_repo.invalidate(product.id)
```

## Traced Repository

Wraps any repository with telemetry spans:

```python
from vellum import TracedRepository

traced_repo = TracedRepository(repo)
```
