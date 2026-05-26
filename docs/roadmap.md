# Vellum Roadmap — Next Steps

> This document outlines all planned improvements beyond the initial implementation.
> Each section is a self-contained step that can be implemented independently.
> GitHub issues have been created for each step.

---

## Phase 1: Polish & Quality

### Step 1 — Package typing marker + lint config

**Files:**
- Create: `src/vellum/py.typed`
- Modify: `pyproject.toml` (ruff config)
- Modify: all source files (fix ruff violations)

**What:**
Add a `py.typed` marker file so mypy/pyright understand Vellum is typed.
Add a `[tool.ruff]` section to pyproject.toml with line length, import order,
and selected rules. Run ruff --fix across the codebase.

**Why:**
Without `py.typed`, downstream projects won't get type-checking benefits even
though we use generics and type annotations everywhere.

---

### Step 2 — Enhanced README

**Files:**
- Modify: `README.md`

**What:**
Replace the minimal README with a proper one including:
- Quick-start code snippet (create model, CRUD, aggregation)
- Feature list with badges
- Installation instructions
- Link to docs/learning.md
- Link to full API reference (once mkdocs is set up)

---

### Step 3 — GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

**What:**
A CI workflow that:
1. Starts MongoDB via `mongosh` or `docker compose`
2. Runs `pytest tests/ --ignore=tests/test_transactions.py -v`
3. Runs `ruff check src/`
4. Runs `mypy src/` (optional, nice-to-have)

**Why:**
Every commit should be verified automatically. Manual testing doesn't scale.

---

## Phase 2: Missing Repository Methods

### Step 4 — Convenience query methods

**Files:**
- Modify: `src/vellum/repository.py`
- Modify: `tests/test_repository.py`

**What:**
Add these methods to `VellumRepository`:

```python
async def find_one(self, query: Dict[str, Any] = {}) -> Optional[T]:
    """Return the first matching document or None."""

async def find_or_create(
    self, query: Dict[str, Any], defaults: Dict[str, Any]
) -> Tuple[T, bool]:
    """Find or create a document. Returns (item, was_created)."""

async def upsert(
    self, query: Dict[str, Any], item: T
) -> T:
    """Update matching document or insert if none matches."""
```

Each method respects soft-delete filtering and OCC where applicable.

---

### Step 5 — Bulk operations

**Files:**
- Modify: `src/vellum/repository.py`
- Modify: `tests/test_repository.py`

**What:**
Add bulk methods using MongoDB's `insert_many`, `update_many`, `delete_many`:

```python
async def bulk_create(self, items: List[T]) -> List[T]:
async def bulk_update(self, items: List[Tuple[UUID, T]]) -> List[T]:
async def bulk_delete(self, ids: List[UUID]) -> int:
```

**Why:**
Batch processing (imports, migrations) is orders of magnitude faster with bulk
ops than individual create/update calls.

---

## Phase 3: Field Reference System

### Step 6 — Type-safe field references

**Files:**
- Create: `src/vellum/fields.py`
- Modify: `src/vellum/query.py`
- Modify: `tests/test_query.py`

**What:**
Replace string-based field paths with property-style references:

```python
# Before (stringly-typed):
results = await repo.find({"age": {"$gt": 18}})
q = Eq("name", "Alice") & Gt("age", 18)

# After (type-safe, IDE autocomplete):
results = await repo.find(User.age > 18)
q = (User.name == "Alice") & (User.age > 18)
```

**How it works:**
Each `VellumBaseModel` subclass gets a `FieldDescriptor` for each field that
returns a proxy object. The proxy supports `==`, `!=`, `>`, `<`, `>=`, `<=`,
`in_`, `not_in_` etc., and compiles to the same MongoDB query dicts.

```python
class FieldDescriptor:
    """Descriptor that returns a FieldProxy when accessed on the class."""

    def __get__(self, obj, objtype=None):
        if obj is None:
            return FieldProxy(self.field_name)
        return obj.__dict__[self.field_name]

result = FieldProxy("age") > 18  # -> Gt("age", 18)
```

**Why this matters:**
This is the single biggest UX differentiator vs raw pymongo. It gives you
IDE autocomplete, rename safety, and compile-time error detection for field
names — without sacrificing any expressiveness.

---

## Phase 4: Advanced Query Operators

### Step 7 — Geospatial query operators

**Files:**
- Modify: `src/vellum/query.py`
- Modify: `tests/test_query.py`

**What:**
Add operators for MongoDB geospatial queries:

```python
class Near(FieldQueryExpression):
    """$near — find points near a coordinate."""

class GeoWithin(FieldQueryExpression):
    """$geoWithin — find points within a shape."""

class GeoIntersects(FieldQueryExpression):
    """$geoIntersects — find geometries that intersect."""
```

Each maps to a helper function (`near()`, `geo_within()`, `geo_intersects()`).

**Why:**
Location-based queries are a common MongoDB use case (delivery apps, store
locators, travel). Without these, users must drop to raw dicts.

---

### Step 8 — Text search support

**Files:**
- Modify: `src/vellum/query.py`
- Modify: `tests/test_query.py`

**What:**
Add a `Text` query expression:

```python
class Text(QueryExpression):
    """$text — full-text search on a text index."""

    def __init__(self, search: str, language: Optional[str] = None,
                 case_sensitive: bool = False, diacritic_sensitive: bool = False):
        ...
```

Plus helper: `text("search string", language="en")`.

**Why:**
MongoDB text indexes are powerful (stemming, stop words, scoring). A first-class
`Text` operator makes them discoverable and type-safe.

---

## Phase 5: Embedded Documents & Schema

### Step 9 — Embedded document support

**Files:**
- Create: `tests/test_embedded.py`

**What:**
Document and test the pattern for nested Pydantic models. Pydantic v2 already
supports this natively — the step is about documenting the correct approach
and adding helper types.

```python
class Address(VellumBaseModel):
    city: str
    country: str

class User(VellumBaseModel):
    name: str
    address: Address  # nested — works out of the box
```

Add tests verifying:
- to_mongo serialises nested models correctly
- from_mongo restores nested models
- Querying on nested fields (`Eq("address.city", "London")`)

**Why:**
Embedded documents are a core MongoDB pattern (denormalization). Users need to
know this works and how to query them.

---

### Step 10 — MongoDB schema validation helpers

**Files:**
- Modify: `src/vellum/repository.py`
- Tests in `tests/test_repository.py`

**What:**
Add a method that generates a MongoDB JSON Schema validator from the Pydantic
model and applies it to the collection:

```python
async def apply_schema_validation(self) -> None:
    """Set collection-level schema validation from Pydantic field types."""
```

This translates Pydantic types to MongoDB JSON Schema:
- `str` → `{"bsonType": "string"}`
- `int` → `{"bsonType": "int"}`
- `float` → `{"bsonType": "double"}`
- `Optional[str]` → add `"type": ["string", "null"]`

**Why:**
Server-side validation catches data quality issues at the database level,
before they reach application code. It's a safety net.

---

## Phase 6: Documentation & Infrastructure

### Step 11 — MkDocs site with API reference

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/index.md`
- Create: `docs/api/` (per-module reference pages)
- Modify: `pyproject.toml` (mkdocs config is already there)

**What:**
Set up a full documentation site using mkdocs-material (already a dependency):
- Landing page with feature overview
- Quick-start guide
- Full API reference (auto-generated from docstrings)
- Link to learning.md and roadmap.md
- Deploy via GitHub Pages

**Why:**
A polished documentation site is what separates a hobby project from a library
people actually adopt. mkdocs-material generates beautiful sites with zero
frontend work.
