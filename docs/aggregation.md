# Aggregation Pipeline

Build MongoDB aggregation pipelines with a fluent builder.

## Setup

```python
from vellum import AggregationPipeline

pipeline = AggregationPipeline(repo.collection)
```

## Stages

### $match

```python
results = await pipeline.match({"status": "active"}).execute()
```

### $group

```python
results = await (
    pipeline
    .group("$category", total={"$sum": 1}, avg_price={"$avg": "$price"})
    .execute()
)
```

### $project

```python
results = await pipeline.project({"name": 1, "price": 1, "_id": 0}).execute()
```

### $sort

```python
from vellum import FieldRef

quantity = FieldRef("quantity")
results = await pipeline.sort(quantity.desc()).execute()
# Or: pipeline.sort([("quantity", -1)])
```

### $limit / $skip

```python
results = await pipeline.sort(quantity.desc()).limit(5).skip(10).execute()
```

### $unwind

```python
results = await pipeline.unwind("$items").execute()
# With options: pipeline.unwind({"path": "$items", "preserveNullAndEmptyArrays": True})
```

### $lookup (join)

```python
results = await (
    pipeline
    .lookup(
        from_collection="orders",
        local_field="user_id",
        foreign_field="_id",
        as_field="orders",
    )
    .execute()
)
```

### $addFields

```python
results = await pipeline.add_fields({"total": {"$multiply": ["$price", "$quantity"]}}).execute()
```

### $count

```python
results = await pipeline.count("total").execute()
# Returns [{"total": 42}]
```

## Output Models

Validate aggregation results with Pydantic models:

```python
from pydantic import BaseModel

class RevenueByCategory(BaseModel):
    category: str
    total_revenue: float

results = await (
    pipeline
    .group("$category", total_revenue={"$sum": "$revenue"})
    .sort([("total_revenue", -1)])
    .execute(output_model=RevenueByCategory)
)
# results: list[RevenueByCategory]
```
