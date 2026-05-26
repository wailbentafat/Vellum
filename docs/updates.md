# Updates

Use `UpdateBuilder` for fine-grained MongoDB update operations.

## Setup

```python
from vellum import UpdateBuilder

builder = UpdateBuilder(repo.collection, doc_id)
```

## Operations

```python
# $set — set a field value
await (UpdateBuilder(repo.collection, doc_id)
    .set(Product.price, 29.99)
    .execute()
)

# $unset — remove a field
await (UpdateBuilder(repo.collection, doc_id)
    .unset(Product.tags)
    .execute()
)

# $inc — increment a numeric field
await (UpdateBuilder(repo.collection, doc_id)
    .inc(Product.quantity, 1)
    .execute()
)

# $push — add to an array field
await (UpdateBuilder(repo.collection, doc_id)
    .push(Product.tags, "new-tag")
    .execute()
)

# $pull — remove from an array field
await (UpdateBuilder(repo.collection, doc_id)
    .pull(Product.tags, "old-tag")
    .execute()
)
```

## Chaining

```python
updated_doc = await (
    UpdateBuilder(repo.collection, doc_id)
    .set(Product.price, 29.99)
    .inc(Product.stock, -1)
    .push(Product.tags, "sold")
    .execute()
)
```

## Automatic Timestamps

`UpdateBuilder` automatically adds `updated_at` to the `$set` operation, keeping the model's timestamp in sync.

## With Transactions

```python
async with repo.transaction() as session:
    await (UpdateBuilder(repo.collection, doc_id, session=session)
        .set(Product.price, 29.99)
        .execute()
    )
```

## Result

`.execute()` returns the updated document dict or `None` if not found.
