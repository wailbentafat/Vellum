# Queries

Vellum supports MongoDB query operators through Python expressions. You can build queries using field references and compose them with `&`, `|`, and `~`.

## Field References

Two equivalent syntaxes:

```python
# Direct (Beanie-style) — requires Python 3.12+
Product.price > 10

# Fields proxy — always available
Product.fields.price > 10
```

Both return `QueryExpression` objects that compile to MongoDB query dicts via `.to_mongo_query()`.

## Comparison Operators

```python
Product.price == 10.0      # {"price": 10.0}
Product.price != 10.0      # {"price": {"$ne": 10.0}}
Product.price > 10.0       # {"price": {"$gt": 10.0}}
Product.price >= 10.0      # {"price": {"$gte": 10.0}}
Product.price < 20.0       # {"price": {"$lt": 20.0}}
Product.price <= 20.0      # {"price": {"$lte": 20.0}}
```

## Array & Set Operators

```python
Product.name.in_(["A", "B"])         # {"name": {"$in": ["A", "B"]}}
Product.name.not_in(["A", "B"])      # {"name": {"$nin": ["A", "B"]}}
Product.tags.size(3)                 # {"tags": {"$size": 3}}
Product.tags.all_(["python", "mongo"])  # {"tags": {"$all": ["python", "mongo"]}}
```

## Element Operators

```python
Product.email.exists()               # {"email": {"$exists": True}}
Product.email.exists(False)          # {"email": {"$exists": False}}
```

## String Operators

```python
Product.name.regex("^Widget")              # {"name": {"$regex": "^Widget"}}
Product.name.regex("^widget", options="i") # {"name": {"$regex": "^widget", "$options": "i"}}
```

## Sub-document / Embedded Fields

```python
Product.fields.address.city == "NYC"    # {"address.city": "NYC"}
Product.fields.address.state != "CA"    # {"address.state": {"$ne": "CA"}}
```

Direct syntax doesn't support chaining for nested fields — use `FieldRef("address.city")` or the fields proxy.

## ElemMatch

```python
from vellum import Gt

inner = Gt("score", 90)
Product.grades.elem_match(inner)    # {"grades": {"$elemMatch": {"score": {"$gt": 90}}}}
```

## Geospatial Operators

```python
# $near
Product.location.near((-73.97, 40.77), max_distance=1000)
Product.location.near((-73.97, 40.77), min_distance=100)

# $nearSphere
Product.location.near_sphere((-73.97, 40.77), max_distance=500)

# $geoWithin
polygon = {"type": "Polygon", "coordinates": [[...]]}
Product.location.geo_within(polygon)

# $geoIntersects
Product.location.geo_intersects(polygon)
```

## Logical Composition

Combine expressions with `&` (AND), `|` (OR), and `~` (NOT):

```python
# AND
(Product.price >= 10.0) & (Product.price <= 30.0)

# OR
(Product.name == "A") | (Product.name == "B")

# NOT (converted to $nor)
~(Product.name == "Widget")

# Mixed
((Product.price >= 10) & (Product.price <= 30)) | (Product.name == "Sale")
```

## Text Search

```python
from vellum import TextSearch

TextSearch("hello").to_mongo_query()
TextSearch("hello", language="en", case_sensitive=True).to_mongo_query()
```

## Using Queries with Repository

Pass the compiled query dict to repository methods:

```python
# As dict
results = await repo.find({"price": {"$gt": 10.0}})

# As expression
expr = (Product.price >= 10.0) & (Product.price <= 30.0)
results = await repo.find(expr.to_mongo_query())
```

## Sorting

```python
# Ascending
+Product.price      # SortSpec("price", 1)
Product.price.asc()

# Descending
-Product.price      # SortSpec("price", -1)
Product.price.desc()

# With repository
results = await repo.find(
    sort=[Product.price.asc()]
)
```

## Free-function Equivalents

All operators also work as standalone functions:

```python
from vellum import gt, eq, lt, in_, regex, near, exists

query = (gt("price", 10) & lt("price", 30)).to_mongo_query()
```
