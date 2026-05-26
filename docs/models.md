# Models

## Defining a Model

Models extend `VellumBaseModel` and use standard Pydantic v2 field declarations:

```python
from vellum import VellumBaseModel

class Product(VellumBaseModel):
    name: str
    price: float
    tags: list[str] = []
    metadata: dict = {}
```

Every model automatically includes:

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Auto-generated primary key (stored as `_id` in MongoDB) |
| `created_at` | `datetime` | UTC timestamp set on creation |
| `updated_at` | `datetime` | UTC timestamp updated on every change |

## Collection Name

Set a custom collection name via the inner `Settings` class:

```python
class Product(VellumBaseModel):
    name: str

    class Settings:
        collection_name = "products"
```

If `collection_name` is not set, it defaults to the lowercase class name (`product`).

## Serialization

```python
# MongoDB-ready dict (id as string, by_alias)
doc = product.to_mongo()
# {"_id": "uuid-string", "name": "Widget", ...}

# Restore from MongoDB dict
restored = Product.from_mongo(doc)
```

## Mixins

### Optimistic Concurrency

```python
from vellum import OptimisticConcurrencyMixin

class Product(OptimisticConcurrencyMixin, VellumBaseModel):
    name: str
```

Adds a `version: int = 1` field. The repository auto-increments it on update and raises `OptimisticLockError` on stale writes.

### Soft Delete

```python
from vellum import SoftDeleteMixin

class Post(SoftDeleteMixin, VellumBaseModel):
    title: str
```

Adds `deleted_at: datetime | None`. Soft-deleted documents are excluded from `find()` and `get()` by default. See [Soft Delete](advanced.md#soft-delete) for details.

### Both Together

```python
class VersionedPost(OptimisticConcurrencyMixin, SoftDeleteMixin, VellumBaseModel):
    title: str
```

Order matters — `OptimisticConcurrencyMixin` first, then `SoftDeleteMixin`, then `VellumBaseModel`.

## Field References

Vellum provides two equivalent ways to reference model fields for queries and sorts:

```python
# Direct syntax (Beanie-style)
Product.price > 10
Product.name == "Widget"

# Fields proxy syntax
Product.fields.price > 10
Product.fields.name == "Widget"
```

Both produce the same `QueryExpression` objects. See [Queries](queries.md) for details.

## Indexes

Define indexes in `Settings` using the type-safe `Index` class:

```python
from vellum import Index

class Product(VellumBaseModel):
    name: str
    email: str

    class Settings:
        collection_name = "products"
        indexes = [
            Index("name"),
            Index("email", unique=True),
            Index("name", "price"),               # compound index
            Index("created_at", expireAfterSeconds=3600),  # TTL index
        ]
```

Or use the raw dict format (still supported):

```python
indexes = [
    {"key": [("name", 1)]},
    {"key": [("email", 1)], "unique": True},
]
```

Field names are validated against the model at runtime. Create indexes with:

```python
await repo.ensure_indexes()
```

## Encryption

Encrypt individual fields transparently:

```python
from vellum import encrypted_field

class User(VellumBaseModel):
    name: str
    ssn: encrypted_field("your-passphrase")  # auto encrypt/decrypt
```

Uses PBKDF2HMAC-SHA256 + Fernet symmetric encryption. Values are encrypted on serialization and decrypted on load.
