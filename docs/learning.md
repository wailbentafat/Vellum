# Vellum — What I Learned Building It

This document explains the problems encountered while building Vellum and the
new concepts introduced along the way. It is written to be read by someone
who built the initial skeleton and wants to understand what went wrong and what
the more advanced patterns mean.

---

## Part 1: Bugs in the Original Code

### Bug 1 — `to_mongo()` used ObjectId incorrectly

**The problem:**

```python
data['_id'] = ObjectId(str(data['_id']))  # WRONG
```

`ObjectId(...)` expects either exactly 12 bytes or a 24-character hex string.
A Python UUID printed as a string looks like `550e8400-e29b-41d4-a716-446655440000`
(36 characters, with hyphens). Passing that to `ObjectId` raises `InvalidId`.

**Why it wasn't caught:**
No tests were written, so the error only appeared at runtime.

**The fix:**
Store `_id` as a plain string (`str(uuid)`). MongoDB supports any BSON type
for `_id`, not just ObjectId. A string UUID is readable, unique, and requires
no conversion magic.

---

### Bug 2 — `from_mongo()` converted in the wrong direction

**The problem:**

```python
if '_id' in data and isinstance(data['_id'], str):
    data['_id'] = ObjectId(data['_id'])  # WRONG: str → ObjectId
```

When MongoDB returns a document, `_id` is already the same type it was stored as.
If you stored a string UUID, you get a string UUID back. The code tried to convert
it *to* an ObjectId instead of *back to* a UUID — the opposite of what was needed.

**The fix:**

```python
if '_id' in data and isinstance(data['_id'], str):
    data['_id'] = UUID(data['_id'])  # Correct: str → UUID
```

---

### Bug 3 — `find()` iterated the wrong variable

**The problem:**

```python
processed_query: Dict[str, Any] = {}
for key, value in processed_query:   # BUG: iterating the empty dict, not `query`
    ...
cursor = self.collection.find(processed_query)  # always an empty filter!
```

Two issues:
1. It iterates `processed_query` (always empty at that point) instead of `query`.
2. `for key, value in some_dict` is wrong Python — you need `.items()`.

Every call to `find()` silently returned all documents regardless of the filter.

**The fix:**

```python
for key, value in query.items():
    processed_query[key] = value
```

---

### Bug 4 — `__setattr__` had a silent return path bug

**The problem:**

```python
def __setattr__(self, name, value):
    if name.startswith('model_') or name in [...]:
        super().__setattr__(name, value)
    # Missing `return` — falls through to the rest of the method too!
    ...
```

Without `return` after the early `super().__setattr__()`, the method continued
executing and called `super().__setattr__()` a second time. This caused Pydantic
to be called twice, which could trigger unexpected validation or double-setting
of internal attributes.

**The fix:** Add `return` immediately after the early path.

---

### Bug 5 — Separate `bson` package conflicts with pymongo

**The problem:**

```toml
dependencies = [
    "pymongo>=4.0,<5.0",
    "bson>=0.5,<1.0"   # WRONG
]
```

The `bson` package on PyPI is a *different* package from the `bson` module
bundled inside `pymongo`. Installing both creates a namespace conflict and breaks
pymongo's internal imports. The `bson` module is already available when you
install `pymongo` — do not list it separately.

---

## Part 2: New Concepts

### Concept 1 — Generic Classes (`Generic[T]`)

`VellumRepository` is defined as `class VellumRepository(Generic[T])`.
This is Python's way of writing a *type-parameterized class* — similar to
`List[int]` or `Dict[str, int]`.

```python
T = TypeVar("T", bound=VellumBaseModel)

class VellumRepository(Generic[T]):
    def __init__(self, model_cls: Type[T], ...) -> None: ...
    async def get(self, ...) -> T: ...         # return type is whatever T is
    async def find(self, ...) -> List[T]: ...  # same
```

When you write `VellumRepository(User, db)`, Python's type checker understands
that `repo.get(...)` returns `User`, not a generic `VellumBaseModel`. This gives
you full autocomplete and type safety without writing a separate repository per model.

---

### Concept 2 — Pydantic's `model_validate` vs `__init__`

`cls.model_validate(data)` is Pydantic v2's way to build a model from a dict.
It runs full validation (type coercion, validators, aliases) just like `__init__`,
but is preferred when the source is untyped data (like a MongoDB document).

`model_dump(by_alias=True)` is the reverse: serialize the model to a dict using
the MongoDB field names (e.g., `_id` instead of `id`).

---

### Concept 3 — Optimistic Concurrency Control (OCC)

OCC solves the *lost update* problem without database locks.

**The scenario:**
1. Process A reads document version=1.
2. Process B reads document version=1.
3. Process A updates → version becomes 2.
4. Process B tries to update using `WHERE _id=X AND version=1`.
   MongoDB finds no matching document (version is now 2), so `matched_count=0`.
5. Vellum raises `OptimisticLockError`.

This is safer than locks because:
- No process can "hold" a lock and stall others.
- The failure is explicit — the caller can retry with fresh data.

OCC is the default strategy used by Django's `select_for_update()` alternative
in high-concurrency scenarios.

---

### Concept 4 — Soft Delete

Hard delete removes data permanently. Soft delete sets a `deleted_at` timestamp
instead. The document stays in the database, which means:
- You can audit what was deleted and when.
- You can restore accidentally deleted documents.
- Foreign keys / references don't break.

The tradeoff: your `find` and `count` queries must always include
`{"deleted_at": None}` in their filter, or you'll accidentally surface
deleted records. Vellum handles this automatically when your model uses
`SoftDeleteMixin`.

---

### Concept 5 — Aggregation Pipelines

A MongoDB aggregation pipeline is a sequence of *stages*. Each stage transforms
the documents and passes the result to the next stage. Common stages:

| Stage | Purpose |
|---|---|
| `$match` | Filter (like `find`) |
| `$project` | Include/exclude/compute fields |
| `$group` | Group and aggregate (like SQL GROUP BY) |
| `$sort` | Sort results |
| `$limit` / `$skip` | Paginate |
| `$unwind` | Flatten an array field into separate documents |
| `$lookup` | Left outer join with another collection |
| `$addFields` | Add computed fields without dropping existing ones |
| `$count` | Count documents |

Vellum's `AggregationPipeline` wraps these with a fluent API. The key
differentiator is `output_model`: pass a Pydantic model class to `project()`
or `group()` and `execute()` returns validated instances instead of raw dicts.

---

### Concept 6 — Lifecycle Hooks

Hooks let you add behaviour that runs *around* CRUD operations without modifying
the repository. This is the *Open/Closed Principle*: the repository is closed for
modification but open for extension through hooks.

Common uses:
- **before_insert**: normalize data (e.g. lowercase email), validate business rules.
- **after_insert**: send a welcome email, emit an event.
- **before_delete**: check if deletion is allowed.
- **after_delete**: clean up related files or cache.

Raising any exception from a `before_*` hook cancels the operation.

---

### Concept 7 — Context Managers for Transactions

```python
async with repo.transaction() as session:
    await repo.update(a.id, a, session=session)
    await repo.update(b.id, b, session=session)
```

If any operation inside the `with` block raises an exception, MongoDB rolls back
all changes made in that block — none of them are persisted. This is what
"ACID" means: Atomicity, Consistency, Isolation, Durability.

**Important:** MongoDB transactions require a *replica set* (at least one primary
+ one secondary). A standalone server (like the one in docker-compose for tests)
does not support multi-document transactions. This is a common source of confusion.

---

### Concept 8 — FastAPI Dependency Injection

FastAPI's `Depends` system lets you declare *what* a route needs without
knowing *how* to create it. `repository_factory` produces a dependency function
that FastAPI calls automatically:

```python
user_repo_dep = repository_factory(User, get_db)

@app.get("/users/{uid}")
async def get_user(uid: str, repo = Depends(user_repo_dep)):
    return await repo.get(uid)
```

FastAPI resolves the dependency tree, calls `get_db()` to get the database,
creates the repository, and passes it to your route — all automatically.
This makes routes easy to test: just override the dependency in tests.
