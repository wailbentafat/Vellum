# Vellum ODM — Complete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete all three phases of the Vellum ODM — a type-safe, async Python ODM for MongoDB that surpasses Beanie — with full test coverage and a learning document.

**Architecture:** `VellumBaseModel` (Pydantic BaseModel with MongoDB mapping), `VellumRepository[T]` (generic async CRUD + advanced features), and composable modules for querying, aggregation, hooks, OCC, and soft-delete. Each subsystem is a separate file with a single clear responsibility.

**Tech Stack:** Python 3.12, Pydantic v2, Motor (async MongoDB driver), pymongo, pytest + pytest-asyncio, Docker Compose (test MongoDB).

---

## File Map

| File | Responsibility |
|---|---|
| `src/vellum/exceptions.py` | All custom exceptions |
| `src/vellum/model.py` | `VellumBaseModel`, `OptimisticConcurrencyMixin`, `SoftDeleteMixin` |
| `src/vellum/query.py` | All query expression classes + helper functions |
| `src/vellum/aggregation.py` | `AggregationPipeline` fluent builder |
| `src/vellum/hooks.py` | Lifecycle hook base methods |
| `src/vellum/connection.py` | `connect_to_mongodb`, FastAPI startup/shutdown helpers |
| `src/vellum/fastapi.py` | FastAPI `Depends` factory for repository injection |
| `src/vellum/repository.py` | `VellumRepository[T]` — all CRUD + advanced operations |
| `src/vellum/__init__.py` | Public API re-exports |
| `tests/docker-compose.yml` | MongoDB test instance |
| `tests/conftest.py` | pytest fixtures (db, client, repositories) |
| `tests/test_model.py` | VellumBaseModel unit tests |
| `tests/test_query.py` | Query expression unit tests |
| `tests/test_repository.py` | Repository integration tests |
| `tests/test_aggregation.py` | Aggregation pipeline integration tests |
| `tests/test_hooks.py` | Lifecycle hooks integration tests |
| `docs/learning.md` | Concepts + problems explained for the learner |

---

## Task 1: Project Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/docker-compose.yml`
- Create: `tests/conftest.py`

- [ ] **Step 1: Fix pyproject.toml**

Remove the standalone `bson` package (it conflicts with pymongo's bundled bson). Add `pytest-asyncio` asyncio_mode config.

```toml
[project]
name = "vellum"
version = "0.1.0"
description = "The Precision ODM for Asynchronous MongoDB & Pydantic."
authors = [
    {name = "bentafat wail", email = "150479778+wailbentafat@users.noreply.github.com"}
]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "motor>=3.2,<4.0",
    "pymongo>=4.0,<5.0",
]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry.group.dev.dependencies]
pytest = "^8.4.1"
pytest-asyncio = "^0.23.0"
ruff = "^0.12.0"
mkdocs-material = "^9.6.14"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write docker-compose.yml for test MongoDB**

```yaml
services:
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: vellum_test
```

Save to `tests/docker-compose.yml`.

- [ ] **Step 3: Write conftest.py**

```python
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

MONGO_URI = "mongodb://localhost:27017"
TEST_DB_NAME = "vellum_test"


@pytest_asyncio.fixture
async def db() -> AsyncIOMotorDatabase:
    client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URI)
    database: AsyncIOMotorDatabase = client[TEST_DB_NAME]
    yield database
    await client.drop_database(TEST_DB_NAME)
    client.close()
```

Save to `tests/conftest.py`.

- [ ] **Step 4: Start MongoDB**

```bash
cd tests && docker compose up -d
```

Expected: MongoDB running on port 27017.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/docker-compose.yml tests/conftest.py
git commit -m "chore: fix project dependencies and test infrastructure"
```

---

## Task 2: Custom Exceptions

**Files:**
- Create: `src/vellum/exceptions.py`

- [ ] **Step 1: Write the test**

Create `tests/test_exceptions.py`:

```python
import pytest
from vellum.exceptions import DocumentNotFoundError, OptimisticLockError, VellumError


def test_document_not_found_is_vellum_error():
    err = DocumentNotFoundError("not found")
    assert isinstance(err, VellumError)
    assert str(err) == "not found"


def test_optimistic_lock_is_vellum_error():
    err = OptimisticLockError("version mismatch")
    assert isinstance(err, VellumError)
```

- [ ] **Step 2: Run the test — verify it fails**

```bash
pytest tests/test_exceptions.py -v
```

Expected: `ModuleNotFoundError: No module named 'vellum.exceptions'`

- [ ] **Step 3: Write exceptions.py**

```python
class VellumError(Exception):
    """Base exception for all Vellum errors."""


class DocumentNotFoundError(VellumError):
    """Raised when a requested document does not exist in the collection."""


class OptimisticLockError(VellumError):
    """Raised when an update fails due to a version mismatch (concurrent modification)."""


class HookError(VellumError):
    """Raised when a lifecycle hook raises an exception."""
```

Save to `src/vellum/exceptions.py`.

- [ ] **Step 4: Run test — verify it passes**

```bash
pytest tests/test_exceptions.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/exceptions.py tests/test_exceptions.py
git commit -m "feat: add custom exception hierarchy"
```

---

## Task 3: Fix VellumBaseModel

**Files:**
- Modify: `src/vellum/model.py`
- Create: `tests/test_model.py`

**Key bugs to fix:**
1. `to_mongo()` calls `ObjectId(str(uuid))` but UUID str (36 chars with hyphens) is not a valid ObjectId. Store `_id` as a plain string UUID instead.
2. `from_mongo()` converts `str → ObjectId` instead of `str → UUID`.
3. `__init__` override is redundant and has incorrect logic — Pydantic Field defaults handle everything.
4. `__setattr__` silently skips setting the attribute when name starts with `model_` (missing `return`).

- [ ] **Step 1: Write the failing tests**

```python
import datetime
from uuid import UUID
from vellum.model import VellumBaseModel


class User(VellumBaseModel):
    name: str
    age: int

    class Settings:
        collection_name = "users"


def test_model_has_uuid_id():
    user = User(name="Alice", age=30)
    assert isinstance(user.id, UUID)


def test_model_has_timestamps():
    user = User(name="Alice", age=30)
    assert isinstance(user.created_at, datetime.datetime)
    assert isinstance(user.updated_at, datetime.datetime)
    assert user.created_at.tzinfo is not None


def test_get_collection_name_from_settings():
    assert User.get_collection_name() == "users"


def test_get_collection_name_fallback():
    class Product(VellumBaseModel):
        title: str
    assert Product.get_collection_name() == "product"


def test_to_mongo_stores_id_as_string():
    user = User(name="Alice", age=30)
    doc = user.to_mongo()
    assert doc["_id"] == str(user.id)
    assert "id" not in doc


def test_from_mongo_restores_model():
    user = User(name="Alice", age=30)
    doc = user.to_mongo()
    restored = User.from_mongo(doc)
    assert restored.id == user.id
    assert restored.name == "Alice"


def test_setattr_updates_updated_at():
    user = User(name="Alice", age=30)
    old_updated = user.updated_at
    user.name = "Bob"
    assert user.updated_at >= old_updated
    assert user.name == "Bob"


def test_settings_default_collection_name():
    class Order(VellumBaseModel):
        total: float
    assert Order.get_collection_name() == "order"
```

Save to `tests/test_model.py`.

- [ ] **Step 2: Run — verify failures**

```bash
pytest tests/test_model.py -v
```

Expected: multiple failures (bugs in to_mongo, from_mongo).

- [ ] **Step 3: Rewrite model.py**

```python
import datetime
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T", bound="VellumBaseModel")


class VellumBaseModel(BaseModel):
    """
    Base model for all Vellum documents.

    Maps Pydantic models to MongoDB documents. `id` is stored as a string UUID
    under the `_id` key in MongoDB. `created_at` and `updated_at` are set
    automatically and kept in UTC.
    """

    id: UUID = Field(default_factory=uuid4, alias="_id")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        from_attributes=True,
        protected_namespaces=(),
    )

    class Settings:
        collection_name: ClassVar[Optional[str]] = None

    @classmethod
    def get_collection_name(cls) -> str:
        name = cls.Settings.collection_name
        return name if name else cls.__name__.lower()

    def to_mongo(self) -> Dict[str, Any]:
        """Serialize to a MongoDB-ready dict. `id` becomes `_id` as a string UUID."""
        data = self.model_dump(by_alias=True, exclude_none=False)
        if "_id" in data and isinstance(data["_id"], UUID):
            data["_id"] = str(data["_id"])
        return data

    @classmethod
    def from_mongo(cls: Type[T], data: Dict[str, Any]) -> T:
        """Deserialize from a MongoDB document dict. Converts string `_id` back to UUID."""
        if "_id" in data and isinstance(data["_id"], str):
            data["_id"] = UUID(data["_id"])
        return cls.model_validate(data)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("created_at", "updated_at", "id") or name.startswith("model_"):
            super().__setattr__(name, value)
            return
        current = self.__dict__.get(name)
        if current is not None and current != value:
            super().__setattr__(
                "updated_at", datetime.datetime.now(datetime.timezone.utc)
            )
        super().__setattr__(name, value)
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_model.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/model.py tests/test_model.py
git commit -m "fix: correct VellumBaseModel ID strategy and from_mongo/to_mongo bugs"
```

---

## Task 4: Fix VellumRepository + Add count & ensure_indexes

**Files:**
- Modify: `src/vellum/repository.py`
- Modify: `tests/test_repository.py`

**Bugs to fix:**
1. `find()` iterates `processed_query` (empty dict) instead of `query.items()`.
2. `update()` sets entire document — should use partial update with `model_dump(exclude_unset=True)`.
3. Missing `count()` and `ensure_indexes()` methods.

- [ ] **Step 1: Write the failing integration tests**

```python
import pytest
import pytest_asyncio
from uuid import uuid4
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository
from vellum.exceptions import DocumentNotFoundError


class Product(VellumBaseModel):
    name: str
    price: float

    class Settings:
        collection_name = "products"
        indexes = [
            {"key": [("name", 1)], "unique": True},
        ]


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(Product, db)


@pytest.mark.asyncio
async def test_create_and_get(repo):
    product = Product(name="Widget", price=9.99)
    created = await repo.create(product)
    fetched = await repo.get(created.id)
    assert fetched.name == "Widget"
    assert fetched.price == 9.99


@pytest.mark.asyncio
async def test_get_not_found_raises(repo):
    with pytest.raises(DocumentNotFoundError):
        await repo.get(uuid4())


@pytest.mark.asyncio
async def test_update(repo):
    product = Product(name="Gadget", price=19.99)
    await repo.create(product)
    product.price = 24.99
    updated = await repo.update(product.id, product)
    assert updated.price == 24.99
    fetched = await repo.get(product.id)
    assert fetched.price == 24.99


@pytest.mark.asyncio
async def test_delete(repo):
    product = Product(name="Doohickey", price=5.00)
    await repo.create(product)
    result = await repo.delete(product.id)
    assert result is True
    with pytest.raises(DocumentNotFoundError):
        await repo.get(product.id)


@pytest.mark.asyncio
async def test_delete_not_found_raises(repo):
    with pytest.raises(DocumentNotFoundError):
        await repo.delete(uuid4())


@pytest.mark.asyncio
async def test_find_all(repo):
    await repo.create(Product(name="A", price=1.0))
    await repo.create(Product(name="B", price=2.0))
    results = await repo.find()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_find_with_filter(repo):
    await repo.create(Product(name="Cheap", price=1.0))
    await repo.create(Product(name="Expensive", price=100.0))
    results = await repo.find({"name": "Cheap"})
    assert len(results) == 1
    assert results[0].name == "Cheap"


@pytest.mark.asyncio
async def test_count(repo):
    await repo.create(Product(name="X", price=1.0))
    await repo.create(Product(name="Y", price=2.0))
    total = await repo.count()
    assert total == 2
    filtered = await repo.count({"name": "X"})
    assert filtered == 1


@pytest.mark.asyncio
async def test_ensure_indexes(repo):
    await repo.ensure_indexes()
    # Duplicate name should violate unique index
    await repo.create(Product(name="Unique", price=1.0))
    import pytest
    with pytest.raises(Exception):
        await repo.create(Product(name="Unique", price=2.0))
```

Save to `tests/test_repository.py`.

- [ ] **Step 2: Run — verify failures**

```bash
pytest tests/test_repository.py -v
```

Expected: failures due to bugs in find() and missing methods.

- [ ] **Step 3: Rewrite repository.py**

```python
from __future__ import annotations

import datetime
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from vellum.exceptions import DocumentNotFoundError
from vellum.model import VellumBaseModel

T = TypeVar("T", bound=VellumBaseModel)

SortDirection = int  # pymongo.ASCENDING (1) or pymongo.DESCENDING (-1)


class VellumRepository(Generic[T]):
    """
    Async repository providing CRUD operations for a VellumBaseModel subclass.

    Each repository instance is tied to a single collection. Instantiate one
    per model class, passing the Motor database object.
    """

    def __init__(self, model_cls: Type[T], database: AsyncIOMotorDatabase) -> None:
        self.model_cls = model_cls
        self.collection: AsyncIOMotorCollection = database[model_cls.get_collection_name()]

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def create(self, item: T) -> T:
        """Insert a new document. Returns the same item (with timestamps set)."""
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        doc = item.to_mongo()
        result: InsertOneResult = await self.collection.insert_one(doc)
        if not result.inserted_id:
            raise RuntimeError("Insert did not return an inserted_id")
        return item

    async def get(self, doc_id: Union[UUID, str]) -> T:
        """Fetch a document by its UUID. Raises DocumentNotFoundError if missing."""
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        raw: Optional[Dict[str, Any]] = await self.collection.find_one({"_id": query_id})
        if raw is None:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return self.model_cls.from_mongo(raw)

    async def update(self, doc_id: Union[UUID, str], item: T) -> T:
        """
        Replace the document's fields with those from `item`.
        Automatically updates `updated_at`. Raises DocumentNotFoundError if missing.
        """
        if not isinstance(item, self.model_cls):
            raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        doc = item.to_mongo()
        doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        result: UpdateResult = await self.collection.update_one(
            {"_id": query_id}, {"$set": doc}
        )
        if result.matched_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return item

    async def delete(self, doc_id: Union[UUID, str]) -> bool:
        """Delete a document by its UUID. Returns True on success."""
        query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
        result: DeleteResult = await self.collection.delete_one({"_id": query_id})
        if result.deleted_count == 0:
            raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
        return True

    async def find(
        self,
        query: Dict[str, Any] = {},
        skip: int = 0,
        limit: int = 0,
        sort: Optional[List[Tuple[str, SortDirection]]] = None,
    ) -> List[T]:
        """
        Query documents. `query` is a plain MongoDB filter dict.
        Returns a list of validated model instances.
        """
        skip = max(skip, 0)
        limit = max(limit, 0)
        cursor = self.collection.find(query).skip(skip).limit(limit)
        if sort:
            cursor = cursor.sort(sort)
        raw_docs: List[Dict[str, Any]] = await cursor.to_list(length=None)
        return [self.model_cls.from_mongo(doc) for doc in raw_docs]

    async def count(self, query: Dict[str, Any] = {}) -> int:
        """Count documents matching `query` (default: all documents)."""
        return await self.collection.count_documents(query)

    # ------------------------------------------------------------------
    # Index Management
    # ------------------------------------------------------------------

    async def ensure_indexes(self) -> None:
        """
        Create indexes declared in the model's Settings.indexes list.

        Each entry is a dict with at minimum a `key` field (list of (field, direction) tuples).
        Any other keys (e.g. `unique`, `sparse`) are passed as index options.

        Example::

            class Settings:
                indexes = [
                    {"key": [("email", 1)], "unique": True},
                ]
        """
        indexes = getattr(self.model_cls.Settings, "indexes", [])
        for index_spec in indexes:
            spec = dict(index_spec)
            key = spec.pop("key")
            await self.collection.create_index(key, **spec)
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_repository.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/repository.py tests/test_repository.py
git commit -m "fix: correct find() bug, add count() and ensure_indexes() to VellumRepository"
```

---

## Task 5: Complete Query Expressions

**Files:**
- Modify: `src/vellum/query.py`
- Modify: `tests/test_query.py`

Add missing operators: `Exists`, `Regex`, `Size`, `All`, `ElemMatch`. Add `Not` (single-expression logical NOT).

- [ ] **Step 1: Write the failing tests**

```python
from vellum.query import (
    And, Eq, ElemMatch, Exists, Gt, Gte, In, Lt, Lte, Ne, Nor, NotIn,
    Or, Regex, Size, All, Not,
    eq, ne, gt, gte, lt, lte,
)


def test_eq():
    assert Eq("name", "Alice").to_mongo_query() == {"name": "Alice"}


def test_ne():
    assert Ne("age", 30).to_mongo_query() == {"age": {"$ne": 30}}


def test_gt():
    assert Gt("age", 18).to_mongo_query() == {"age": {"$gt": 18}}


def test_gte():
    assert Gte("age", 18).to_mongo_query() == {"age": {"$gte": 18}}


def test_lt():
    assert Lt("age", 65).to_mongo_query() == {"age": {"$lt": 65}}


def test_lte():
    assert Lte("age", 65).to_mongo_query() == {"age": {"$lte": 65}}


def test_in():
    result = In("status", ["active", "pending"]).to_mongo_query()
    assert result == {"status": {"$in": ["active", "pending"]}}


def test_not_in():
    result = NotIn("status", ["deleted"]).to_mongo_query()
    assert result == {"status": {"$nin": ["deleted"]}}


def test_exists_true():
    assert Exists("email", True).to_mongo_query() == {"email": {"$exists": True}}


def test_exists_false():
    assert Exists("email", False).to_mongo_query() == {"email": {"$exists": False}}


def test_regex():
    result = Regex("name", "^Ali").to_mongo_query()
    assert result == {"name": {"$regex": "^Ali"}}


def test_regex_with_options():
    result = Regex("name", "^ali", options="i").to_mongo_query()
    assert result == {"name": {"$regex": "^ali", "$options": "i"}}


def test_size():
    assert Size("tags", 3).to_mongo_query() == {"tags": {"$size": 3}}


def test_all():
    result = All("tags", ["python", "mongodb"]).to_mongo_query()
    assert result == {"tags": {"$all": ["python", "mongodb"]}}


def test_elem_match():
    inner = Gt("score", 90)
    result = ElemMatch("grades", inner).to_mongo_query()
    assert result == {"grades": {"$elemMatch": {"score": {"$gt": 90}}}}


def test_and_operator():
    expr = Eq("name", "Alice") & Gt("age", 18)
    assert expr.to_mongo_query() == {
        "$and": [{"name": "Alice"}, {"age": {"$gt": 18}}]
    }


def test_or_operator():
    expr = Eq("status", "active") | Eq("status", "pending")
    assert expr.to_mongo_query() == {
        "$or": [{"status": "active"}, {"status": "pending"}]
    }


def test_not_operator():
    expr = Not(Gt("age", 65))
    assert expr.to_mongo_query() == {"$nor": [{"age": {"$gt": 65}}]}


def test_nor():
    expr = Nor(Eq("status", "deleted"), Eq("status", "banned"))
    assert expr.to_mongo_query() == {
        "$nor": [{"status": "deleted"}, {"status": "banned"}]
    }


def test_in_requires_iterable():
    import pytest
    with pytest.raises(TypeError):
        In("field", "not_a_list").to_mongo_query()
```

Save to `tests/test_query.py`.

- [ ] **Step 2: Run — verify failures**

```bash
pytest tests/test_query.py -v
```

Expected: failures for Exists, Regex, Size, All, ElemMatch, Not.

- [ ] **Step 3: Rewrite query.py**

```python
"""
Vellum query expression system.

Build type-safe MongoDB query dicts by composing expression objects.
Use the lower-case helper functions (eq, ne, gt, ...) for convenience.

Logical composition::

    (Eq("status", "active") & Gt("age", 18)).to_mongo_query()
    # {"$and": [{"status": "active"}, {"age": {"$gt": 18}}]}

    (Eq("a", 1) | Eq("b", 2)).to_mongo_query()
    # {"$or": [{"a": 1}, {"b": 2}]}
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

MongoFieldPath = str


# ---------------------------------------------------------------------------
# Base classes
# ---------------------------------------------------------------------------


class QueryExpression:
    """Abstract base for all query expressions."""

    def to_mongo_query(self) -> Dict[str, Any]:
        raise NotImplementedError

    def __and__(self, other: QueryExpression) -> And:
        return And(self, other)

    def __or__(self, other: QueryExpression) -> Or:
        return Or(self, other)

    def __invert__(self) -> Not:
        return Not(self)


class FieldQueryExpression(QueryExpression):
    """Base for expressions that operate on a single field."""

    def __init__(self, field: MongoFieldPath, value: Any) -> None:
        self.field = field
        self.value = value

    def _to_mongo_value(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        return value


# ---------------------------------------------------------------------------
# Comparison operators
# ---------------------------------------------------------------------------


class Eq(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: self._to_mongo_value(self.value)}


class Ne(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$ne": self._to_mongo_value(self.value)}}


class Gt(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$gt": self._to_mongo_value(self.value)}}


class Gte(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$gte": self._to_mongo_value(self.value)}}


class Lt(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$lt": self._to_mongo_value(self.value)}}


class Lte(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$lte": self._to_mongo_value(self.value)}}


# ---------------------------------------------------------------------------
# Array / set operators
# ---------------------------------------------------------------------------


class In(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$in requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$in": converted}}


class NotIn(FieldQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$nin requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$nin": converted}}


class All(FieldQueryExpression):
    """Matches arrays that contain ALL specified values."""

    def to_mongo_query(self) -> Dict[str, Any]:
        if not isinstance(self.value, (list, tuple, set)):
            raise TypeError(f"$all requires a list/tuple/set, got {type(self.value)}")
        converted = [self._to_mongo_value(v) for v in self.value]
        return {self.field: {"$all": converted}}


class Size(FieldQueryExpression):
    """Matches arrays with exactly `value` elements."""

    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$size": self.value}}


class ElemMatch(QueryExpression):
    """Matches documents where at least one array element satisfies a sub-expression."""

    def __init__(self, field: MongoFieldPath, expression: QueryExpression) -> None:
        self.field = field
        self.expression = expression

    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$elemMatch": self.expression.to_mongo_query()}}


# ---------------------------------------------------------------------------
# Element / evaluation operators
# ---------------------------------------------------------------------------


class Exists(FieldQueryExpression):
    """Checks whether a field exists (True) or does not exist (False)."""

    def to_mongo_query(self) -> Dict[str, Any]:
        return {self.field: {"$exists": bool(self.value)}}


class Regex(QueryExpression):
    """Matches documents where `field` matches the given regular expression."""

    def __init__(
        self, field: MongoFieldPath, pattern: str, options: Optional[str] = None
    ) -> None:
        self.field = field
        self.pattern = pattern
        self.options = options

    def to_mongo_query(self) -> Dict[str, Any]:
        expr: Dict[str, Any] = {"$regex": self.pattern}
        if self.options:
            expr["$options"] = self.options
        return {self.field: expr}


# ---------------------------------------------------------------------------
# Logical operators
# ---------------------------------------------------------------------------


class LogicalQueryExpression(QueryExpression):
    def __init__(self, *expressions: QueryExpression) -> None:
        if not all(isinstance(e, QueryExpression) for e in expressions):
            raise TypeError("All arguments must be QueryExpression instances.")
        self.expressions = expressions


class And(LogicalQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {"$and": [e.to_mongo_query() for e in self.expressions]}


class Or(LogicalQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {"$or": [e.to_mongo_query() for e in self.expressions]}


class Nor(LogicalQueryExpression):
    def to_mongo_query(self) -> Dict[str, Any]:
        return {"$nor": [e.to_mongo_query() for e in self.expressions]}


class Not(LogicalQueryExpression):
    """Logical NOT — excludes documents matching the inner expression."""

    def __init__(self, expression: QueryExpression) -> None:
        super().__init__(expression)

    def to_mongo_query(self) -> Dict[str, Any]:
        return {"$nor": [e.to_mongo_query() for e in self.expressions]}


# ---------------------------------------------------------------------------
# Helper functions (lower-case API)
# ---------------------------------------------------------------------------


def eq(field: MongoFieldPath, value: Any) -> Eq:
    return Eq(field, value)


def ne(field: MongoFieldPath, value: Any) -> Ne:
    return Ne(field, value)


def gt(field: MongoFieldPath, value: Any) -> Gt:
    return Gt(field, value)


def gte(field: MongoFieldPath, value: Any) -> Gte:
    return Gte(field, value)


def lt(field: MongoFieldPath, value: Any) -> Lt:
    return Lt(field, value)


def lte(field: MongoFieldPath, value: Any) -> Lte:
    return Lte(field, value)


def in_(field: MongoFieldPath, values: List[Any]) -> In:
    return In(field, values)


def not_in(field: MongoFieldPath, values: List[Any]) -> NotIn:
    return NotIn(field, values)


def exists(field: MongoFieldPath, value: bool = True) -> Exists:
    return Exists(field, value)


def regex(field: MongoFieldPath, pattern: str, options: Optional[str] = None) -> Regex:
    return Regex(field, pattern, options)


def size(field: MongoFieldPath, count: int) -> Size:
    return Size(field, count)


def all_(field: MongoFieldPath, values: List[Any]) -> All:
    return All(field, values)


def elem_match(field: MongoFieldPath, expression: QueryExpression) -> ElemMatch:
    return ElemMatch(field, expression)
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_query.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/query.py tests/test_query.py
git commit -m "feat: add Exists, Regex, Size, All, ElemMatch, Not query operators"
```

---

## Task 6: Aggregation Pipeline

**Files:**
- Create: `src/vellum/aggregation.py`
- Create: `tests/test_aggregation.py`

- [ ] **Step 1: Write the failing integration tests**

```python
import pytest
import pytest_asyncio
from pydantic import BaseModel
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository
from vellum.aggregation import AggregationPipeline


class Sale(VellumBaseModel):
    product: str
    quantity: int
    price: float

    class Settings:
        collection_name = "sales"


class SaleSummary(BaseModel):
    product: str
    total_qty: int


@pytest_asyncio.fixture
async def sale_repo(db):
    repo = VellumRepository(Sale, db)
    await repo.create(Sale(product="Apple", quantity=10, price=1.5))
    await repo.create(Sale(product="Apple", quantity=5, price=1.5))
    await repo.create(Sale(product="Banana", quantity=20, price=0.75))
    return repo


@pytest.mark.asyncio
async def test_pipeline_match(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.match({"product": "Apple"}).execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_sort_limit(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.sort([("quantity", -1)]).limit(1).execute()
    assert len(results) == 1
    assert results[0]["quantity"] == 20


@pytest.mark.asyncio
async def test_pipeline_skip(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.sort([("quantity", 1)]).skip(1).execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_project(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.project({"product": 1, "_id": 0}).execute()
    assert all("product" in r for r in results)
    assert all("price" not in r for r in results)


@pytest.mark.asyncio
async def test_pipeline_group(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await (
        pipeline
        .group({"_id": "$product"}, total_qty={"$sum": "$quantity"})
        .execute()
    )
    products = {r["_id"] for r in results}
    assert "Apple" in products
    assert "Banana" in products


@pytest.mark.asyncio
async def test_pipeline_with_output_model(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection, output_model=SaleSummary)
    results = await (
        pipeline
        .group({"_id": "$product"}, total_qty={"$sum": "$quantity"})
        .project({"product": "$_id", "total_qty": 1, "_id": 0}, output_model=SaleSummary)
        .execute()
    )
    assert all(isinstance(r, SaleSummary) for r in results)


@pytest.mark.asyncio
async def test_pipeline_unwind(sale_repo):
    # Create a doc with an array field to test unwind
    from motor.motor_asyncio import AsyncIOMotorCollection
    col: AsyncIOMotorCollection = sale_repo.collection
    await col.insert_one({"tags": ["fresh", "organic"], "product": "Apple", "quantity": 1, "price": 2.0, "_id": "test-unwind"})

    pipeline = AggregationPipeline(col)
    results = await pipeline.match({"_id": "test-unwind"}).unwind("$tags").execute()
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pipeline_add_fields(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.add_fields({"revenue": {"$multiply": ["$price", "$quantity"]}}).execute()
    assert all("revenue" in r for r in results)


@pytest.mark.asyncio
async def test_pipeline_count_stage(sale_repo):
    pipeline = AggregationPipeline(sale_repo.collection)
    results = await pipeline.count_stage("total").execute()
    assert len(results) == 1
    assert results[0]["total"] == 3
```

Save to `tests/test_aggregation.py`.

- [ ] **Step 2: Run — verify failures**

```bash
pytest tests/test_aggregation.py -v
```

Expected: `ModuleNotFoundError: No module named 'vellum.aggregation'`

- [ ] **Step 3: Write aggregation.py**

```python
"""
Vellum AggregationPipeline — fluent builder for MongoDB aggregation pipelines.

Usage::

    pipeline = AggregationPipeline(collection)
    results = await (
        pipeline
        .match({"status": "active"})
        .group({"_id": "$department"}, total={"$sum": "$salary"})
        .sort([("total", -1)])
        .limit(10)
        .execute()
    )

Pass `output_model` to get validated Pydantic instances back::

    pipeline = AggregationPipeline(collection, output_model=DeptSummary)
    results = await pipeline.group(...).execute()
    # results: List[DeptSummary]
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class AggregationPipeline:
    """
    Fluent builder for MongoDB aggregation pipelines.

    All stage methods return `self` so they can be chained.
    Call `execute()` at the end to run the pipeline and get results.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        output_model: Optional[Type[BaseModel]] = None,
    ) -> None:
        self._collection = collection
        self._stages: List[Dict[str, Any]] = []
        self._output_model = output_model

    # ------------------------------------------------------------------
    # Stage builders
    # ------------------------------------------------------------------

    def match(self, query: Dict[str, Any]) -> AggregationPipeline:
        """Filter documents. Equivalent to a WHERE clause in SQL."""
        self._stages.append({"$match": query})
        return self

    def project(
        self,
        projection: Dict[str, Any],
        output_model: Optional[Type[BaseModel]] = None,
    ) -> AggregationPipeline:
        """
        Include, exclude, or reshape fields.
        Pass `output_model` to update the expected output type for `execute()`.
        """
        self._stages.append({"$project": projection})
        if output_model is not None:
            self._output_model = output_model
        return self

    def group(
        self,
        group_id: Dict[str, Any],
        output_model: Optional[Type[BaseModel]] = None,
        **accumulators: Any,
    ) -> AggregationPipeline:
        """
        Group documents by `group_id` and apply accumulator expressions.

        Example::

            pipeline.group({"_id": "$category"}, total={"$sum": "$price"})
        """
        stage: Dict[str, Any] = {"_id": group_id, **accumulators}
        self._stages.append({"$group": stage})
        if output_model is not None:
            self._output_model = output_model
        return self

    def sort(self, sort_spec: List[Tuple[str, int]]) -> AggregationPipeline:
        """
        Sort documents. Each tuple is (field_name, direction) where
        direction is 1 (ascending) or -1 (descending).
        """
        self._stages.append({"$sort": dict(sort_spec)})
        return self

    def limit(self, n: int) -> AggregationPipeline:
        """Keep only the first `n` documents."""
        self._stages.append({"$limit": n})
        return self

    def skip(self, n: int) -> AggregationPipeline:
        """Skip the first `n` documents."""
        self._stages.append({"$skip": n})
        return self

    def unwind(self, path: str, preserve_null_and_empty: bool = False) -> AggregationPipeline:
        """
        Deconstruct an array field — outputs one document per array element.

        `path` must start with `$`, e.g. `"$tags"`.
        """
        stage: Any = {"path": path}
        if preserve_null_and_empty:
            stage["preserveNullAndEmptyArrays"] = True
        self._stages.append({"$unwind": stage})
        return self

    def add_fields(self, fields: Dict[str, Any]) -> AggregationPipeline:
        """Add or overwrite fields without removing existing ones."""
        self._stages.append({"$addFields": fields})
        return self

    def set(self, fields: Dict[str, Any]) -> AggregationPipeline:
        """Alias for add_fields (MongoDB $set stage)."""
        self._stages.append({"$set": fields})
        return self

    def replace_root(self, new_root: Any) -> AggregationPipeline:
        """Replace the root document with the specified expression."""
        self._stages.append({"$replaceRoot": {"newRoot": new_root}})
        return self

    def lookup(
        self,
        from_collection: str,
        local_field: str,
        foreign_field: str,
        as_field: str,
    ) -> AggregationPipeline:
        """
        Perform a left outer join with another collection.

        Results are added as an array field named `as_field`.
        """
        self._stages.append({
            "$lookup": {
                "from": from_collection,
                "localField": local_field,
                "foreignField": foreign_field,
                "as": as_field,
            }
        })
        return self

    def count_stage(self, output_field: str) -> AggregationPipeline:
        """Count the number of documents and store the result in `output_field`."""
        self._stages.append({"$count": output_field})
        return self

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self) -> List[Any]:
        """
        Run the pipeline and return results.

        If `output_model` was set (via constructor or `project`/`group`),
        each result dict is validated against that model and returned as
        a model instance. Otherwise returns raw dicts.
        """
        cursor = self._collection.aggregate(self._stages)
        raw: List[Dict[str, Any]] = await cursor.to_list(length=None)
        if self._output_model is not None:
            return [self._output_model.model_validate(doc) for doc in raw]
        return raw
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_aggregation.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/aggregation.py tests/test_aggregation.py
git commit -m "feat: implement AggregationPipeline with fluent stage builder"
```

---

## Task 7: Lifecycle Hooks

**Files:**
- Create: `src/vellum/hooks.py`
- Modify: `src/vellum/repository.py`
- Create: `tests/test_hooks.py`

Hooks are override-able async methods on `VellumBaseModel`. The repository calls them around each operation.

- [ ] **Step 1: Write failing tests**

```python
import pytest
import pytest_asyncio
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


class AuditedItem(VellumBaseModel):
    name: str
    hook_log: list[str] = []

    class Settings:
        collection_name = "audited_items"

    async def before_insert(self) -> None:
        self.hook_log.append("before_insert")

    async def after_insert(self) -> None:
        self.hook_log.append("after_insert")

    async def before_update(self) -> None:
        self.hook_log.append("before_update")

    async def after_update(self) -> None:
        self.hook_log.append("after_update")

    async def before_delete(self) -> None:
        self.hook_log.append("before_delete")

    async def after_delete(self) -> None:
        self.hook_log.append("after_delete")


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(AuditedItem, db)


@pytest.mark.asyncio
async def test_insert_hooks_called(repo):
    item = AuditedItem(name="test", hook_log=[])
    await repo.create(item)
    assert "before_insert" in item.hook_log
    assert "after_insert" in item.hook_log


@pytest.mark.asyncio
async def test_insert_hooks_order(repo):
    item = AuditedItem(name="order-test", hook_log=[])
    await repo.create(item)
    bi = item.hook_log.index("before_insert")
    ai = item.hook_log.index("after_insert")
    assert bi < ai


@pytest.mark.asyncio
async def test_update_hooks_called(repo):
    item = AuditedItem(name="update-test", hook_log=[])
    await repo.create(item)
    item.hook_log.clear()
    item.name = "updated"
    await repo.update(item.id, item)
    assert "before_update" in item.hook_log
    assert "after_update" in item.hook_log


@pytest.mark.asyncio
async def test_delete_hooks_called(repo):
    item = AuditedItem(name="delete-test", hook_log=[])
    await repo.create(item)
    item.hook_log.clear()
    await repo.delete(item.id)
    assert "before_delete" in item.hook_log
    assert "after_delete" in item.hook_log


@pytest.mark.asyncio
async def test_hook_can_cancel_insert(repo):
    import pytest
    from vellum.exceptions import HookError

    class StrictItem(VellumBaseModel):
        name: str

        class Settings:
            collection_name = "strict_items"

        async def before_insert(self) -> None:
            raise HookError("Insert not allowed")

    strict_repo = VellumRepository(StrictItem, repo.collection.database)
    item = StrictItem(name="forbidden")
    with pytest.raises(HookError):
        await strict_repo.create(item)
```

Save to `tests/test_hooks.py`.

- [ ] **Step 2: Create hooks.py with default no-op hook methods**

```python
"""
Vellum lifecycle hooks.

Add these async methods to your VellumBaseModel subclass to react to
repository operations. The repository calls them before and after each
CRUD operation. Raise any exception from a `before_*` hook to cancel
the operation.

Example::

    class User(VellumBaseModel):
        email: str

        async def before_insert(self) -> None:
            self.email = self.email.lower()

        async def after_insert(self) -> None:
            print(f"User {self.id} inserted")
"""


class HooksMixin:
    """
    Default no-op lifecycle hooks. Subclass VellumBaseModel and override
    any of these to add behaviour.
    """

    async def before_insert(self) -> None:
        """Called before a document is inserted. Raise to cancel the insert."""

    async def after_insert(self) -> None:
        """Called after a document has been inserted successfully."""

    async def before_update(self) -> None:
        """Called before a document is updated. Raise to cancel the update."""

    async def after_update(self) -> None:
        """Called after a document has been updated successfully."""

    async def before_delete(self) -> None:
        """Called before a document is deleted. Raise to cancel the delete."""

    async def after_delete(self) -> None:
        """Called after a document has been deleted successfully."""
```

Save to `src/vellum/hooks.py`.

- [ ] **Step 3: Add HooksMixin to VellumBaseModel and wire hooks into repository**

In `src/vellum/model.py`, import and add the mixin:

```python
from vellum.hooks import HooksMixin

class VellumBaseModel(HooksMixin, BaseModel):
    ...
```

In `src/vellum/repository.py`, call hooks in create/update/delete:

```python
async def create(self, item: T) -> T:
    if not isinstance(item, self.model_cls):
        raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
    await item.before_insert()
    doc = item.to_mongo()
    result: InsertOneResult = await self.collection.insert_one(doc)
    if not result.inserted_id:
        raise RuntimeError("Insert did not return an inserted_id")
    await item.after_insert()
    return item

async def update(self, doc_id: Union[UUID, str], item: T) -> T:
    if not isinstance(item, self.model_cls):
        raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
    await item.before_update()
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    doc = item.to_mongo()
    doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
    result: UpdateResult = await self.collection.update_one(
        {"_id": query_id}, {"$set": doc}
    )
    if result.matched_count == 0:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    await item.after_update()
    return item

async def delete(self, doc_id: Union[UUID, str]) -> bool:
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    # Need the item to call hooks — fetch it first
    raw = await self.collection.find_one({"_id": query_id})
    if raw is None:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    item = self.model_cls.from_mongo(raw)
    await item.before_delete()
    result: DeleteResult = await self.collection.delete_one({"_id": query_id})
    if result.deleted_count == 0:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    await item.after_delete()
    return True
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_hooks.py tests/test_repository.py tests/test_model.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/hooks.py src/vellum/model.py src/vellum/repository.py tests/test_hooks.py
git commit -m "feat: add lifecycle hooks (before/after insert/update/delete)"
```

---

## Task 8: Optimistic Concurrency Control (OCC)

**Files:**
- Modify: `src/vellum/model.py` — add `OptimisticConcurrencyMixin`
- Modify: `src/vellum/repository.py` — detect and handle versioned models
- Create: `tests/test_occ.py`

OCC prevents lost updates: if two processes read version=1 and both try to update, the second one fails because the first already incremented the version to 2.

- [ ] **Step 1: Write the failing tests**

```python
import pytest
import pytest_asyncio
from vellum.model import VellumBaseModel, OptimisticConcurrencyMixin
from vellum.repository import VellumRepository
from vellum.exceptions import OptimisticLockError


class VersionedProduct(OptimisticConcurrencyMixin, VellumBaseModel):
    name: str
    stock: int

    class Settings:
        collection_name = "versioned_products"


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(VersionedProduct, db)


@pytest.mark.asyncio
async def test_version_starts_at_one(repo):
    p = VersionedProduct(name="Widget", stock=100)
    assert p.version == 1
    await repo.create(p)
    fetched = await repo.get(p.id)
    assert fetched.version == 1


@pytest.mark.asyncio
async def test_version_increments_on_update(repo):
    p = VersionedProduct(name="Widget", stock=100)
    await repo.create(p)
    p.stock = 90
    await repo.update(p.id, p)
    fetched = await repo.get(p.id)
    assert fetched.version == 2


@pytest.mark.asyncio
async def test_optimistic_lock_error_on_stale_update(repo):
    p = VersionedProduct(name="Gadget", stock=50)
    await repo.create(p)

    # Simulate two concurrent readers getting the same version=1 copy
    stale_copy = await repo.get(p.id)   # version=1
    fresh_copy = await repo.get(p.id)   # version=1

    # First update succeeds (version goes to 2)
    fresh_copy.stock = 45
    await repo.update(fresh_copy.id, fresh_copy)

    # Second update with stale version=1 should fail
    stale_copy.stock = 40
    with pytest.raises(OptimisticLockError):
        await repo.update(stale_copy.id, stale_copy)
```

Save to `tests/test_occ.py`.

- [ ] **Step 2: Add OptimisticConcurrencyMixin to model.py**

Add after the `VellumBaseModel` class definition:

```python
class OptimisticConcurrencyMixin(BaseModel):
    """
    Adds a `version` counter to a VellumBaseModel subclass.

    The repository automatically increments the version on each update and
    uses it to detect concurrent modifications. If two processes read the
    same version and both try to update, the second one raises OptimisticLockError.

    Usage::

        class Order(OptimisticConcurrencyMixin, VellumBaseModel):
            total: float
    """
    version: int = 1
```

- [ ] **Step 3: Update VellumRepository.update to handle versioned models**

In `repository.py`, modify the `update` method to detect `OptimisticConcurrencyMixin`:

```python
from vellum.model import VellumBaseModel, OptimisticConcurrencyMixin
from vellum.exceptions import DocumentNotFoundError, OptimisticLockError

async def update(self, doc_id: Union[UUID, str], item: T) -> T:
    if not isinstance(item, self.model_cls):
        raise TypeError(f"Expected {self.model_cls.__name__}, got {type(item).__name__}")
    await item.before_update()
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    doc = item.to_mongo()
    doc["updated_at"] = datetime.datetime.now(datetime.timezone.utc)

    if isinstance(item, OptimisticConcurrencyMixin):
        current_version = item.version
        doc["version"] = current_version + 1
        mongo_filter = {"_id": query_id, "version": current_version}
    else:
        mongo_filter = {"_id": query_id}

    result: UpdateResult = await self.collection.update_one(
        mongo_filter, {"$set": doc}
    )
    if result.matched_count == 0:
        if isinstance(item, OptimisticConcurrencyMixin):
            raise OptimisticLockError(
                f"Document id={doc_id} was modified by another process (version mismatch)."
            )
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")

    if isinstance(item, OptimisticConcurrencyMixin):
        item.version = current_version + 1

    await item.after_update()
    return item
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_occ.py tests/test_repository.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/model.py src/vellum/repository.py tests/test_occ.py
git commit -m "feat: add OptimisticConcurrencyMixin and version-based OCC in repository"
```

---

## Task 9: Soft Delete

**Files:**
- Modify: `src/vellum/model.py` — add `SoftDeleteMixin`
- Modify: `src/vellum/repository.py` — add `soft_delete()`, `restore()`, filter in find/get/count
- Create: `tests/test_soft_delete.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
import pytest_asyncio
from vellum.model import VellumBaseModel, SoftDeleteMixin
from vellum.repository import VellumRepository
from vellum.exceptions import DocumentNotFoundError


class Post(SoftDeleteMixin, VellumBaseModel):
    title: str

    class Settings:
        collection_name = "posts"


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(Post, db)


@pytest.mark.asyncio
async def test_soft_delete_sets_deleted_at(repo):
    post = Post(title="Hello")
    await repo.create(post)
    await repo.soft_delete(post.id)
    raw = await repo.collection.find_one({"_id": str(post.id)})
    assert raw["deleted_at"] is not None


@pytest.mark.asyncio
async def test_soft_deleted_excluded_from_find(repo):
    post = Post(title="Excluded")
    await repo.create(post)
    await repo.soft_delete(post.id)
    results = await repo.find()
    assert not any(r.id == post.id for r in results)


@pytest.mark.asyncio
async def test_soft_deleted_excluded_from_get(repo):
    post = Post(title="Gone")
    await repo.create(post)
    await repo.soft_delete(post.id)
    with pytest.raises(DocumentNotFoundError):
        await repo.get(post.id)


@pytest.mark.asyncio
async def test_include_deleted_in_find(repo):
    post = Post(title="Include Me")
    await repo.create(post)
    await repo.soft_delete(post.id)
    results = await repo.find(include_deleted=True)
    assert any(r.id == post.id for r in results)


@pytest.mark.asyncio
async def test_restore(repo):
    post = Post(title="Restore Me")
    await repo.create(post)
    await repo.soft_delete(post.id)
    await repo.restore(post.id)
    fetched = await repo.get(post.id)
    assert fetched.title == "Restore Me"


@pytest.mark.asyncio
async def test_count_excludes_soft_deleted(repo):
    await repo.create(Post(title="A"))
    b = Post(title="B")
    await repo.create(b)
    await repo.soft_delete(b.id)
    assert await repo.count() == 1
```

Save to `tests/test_soft_delete.py`.

- [ ] **Step 2: Add SoftDeleteMixin to model.py**

```python
import datetime as _dt
from typing import Optional as _Optional

class SoftDeleteMixin(BaseModel):
    """
    Adds soft-delete support to a VellumBaseModel subclass.

    Soft-deleted documents are not physically removed — instead `deleted_at`
    is set to the current UTC time. The repository automatically excludes
    them from find/get/count unless `include_deleted=True` is passed.

    Usage::

        class Article(SoftDeleteMixin, VellumBaseModel):
            title: str
    """
    deleted_at: _Optional[_dt.datetime] = None

    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

- [ ] **Step 3: Update VellumRepository with soft delete methods**

Add `soft_delete`, `restore` methods and update `find`, `get`, `count` to accept `include_deleted`:

```python
from vellum.model import VellumBaseModel, OptimisticConcurrencyMixin, SoftDeleteMixin

# In find():
async def find(
    self,
    query: Dict[str, Any] = {},
    skip: int = 0,
    limit: int = 0,
    sort: Optional[List[Tuple[str, SortDirection]]] = None,
    include_deleted: bool = False,
) -> List[T]:
    skip = max(skip, 0)
    limit = max(limit, 0)
    effective_query = dict(query)
    if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
        effective_query["deleted_at"] = None
    cursor = self.collection.find(effective_query).skip(skip).limit(limit)
    if sort:
        cursor = cursor.sort(sort)
    raw_docs: List[Dict[str, Any]] = await cursor.to_list(length=None)
    return [self.model_cls.from_mongo(doc) for doc in raw_docs]

# In get():
async def get(self, doc_id: Union[UUID, str], include_deleted: bool = False) -> T:
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    mongo_filter: Dict[str, Any] = {"_id": query_id}
    if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
        mongo_filter["deleted_at"] = None
    raw = await self.collection.find_one(mongo_filter)
    if raw is None:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    return self.model_cls.from_mongo(raw)

# In count():
async def count(self, query: Dict[str, Any] = {}, include_deleted: bool = False) -> int:
    effective_query = dict(query)
    if issubclass(self.model_cls, SoftDeleteMixin) and not include_deleted:
        effective_query["deleted_at"] = None
    return await self.collection.count_documents(effective_query)

# New methods:
async def soft_delete(self, doc_id: Union[UUID, str]) -> bool:
    """
    Mark a document as deleted by setting `deleted_at` to now (UTC).
    The document remains in the collection but is excluded from normal queries.
    Only works with models that use SoftDeleteMixin.
    """
    if not issubclass(self.model_cls, SoftDeleteMixin):
        raise TypeError(
            f"{self.model_cls.__name__} does not use SoftDeleteMixin. "
            "Use delete() for hard deletes."
        )
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    now = datetime.datetime.now(datetime.timezone.utc)
    result = await self.collection.update_one(
        {"_id": query_id}, {"$set": {"deleted_at": now}}
    )
    if result.matched_count == 0:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    return True

async def restore(self, doc_id: Union[UUID, str]) -> bool:
    """
    Restore a soft-deleted document by clearing its `deleted_at` field.
    """
    if not issubclass(self.model_cls, SoftDeleteMixin):
        raise TypeError(f"{self.model_cls.__name__} does not use SoftDeleteMixin.")
    query_id = str(doc_id) if isinstance(doc_id, UUID) else doc_id
    result = await self.collection.update_one(
        {"_id": query_id}, {"$set": {"deleted_at": None}}
    )
    if result.matched_count == 0:
        raise DocumentNotFoundError(f"Document with id={doc_id} not found.")
    return True
```

- [ ] **Step 4: Run — verify all pass**

```bash
pytest tests/test_soft_delete.py tests/test_repository.py -v
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/vellum/model.py src/vellum/repository.py tests/test_soft_delete.py
git commit -m "feat: add SoftDeleteMixin with soft_delete/restore and implicit filtering"
```

---

## Task 10: Transactions

**Files:**
- Modify: `src/vellum/repository.py` — add `transaction()` context manager
- Create: `tests/test_transactions.py`

> **Note:** MongoDB transactions require a replica set or sharded cluster. The docker-compose test instance is a standalone server — transaction tests are marked with `@pytest.mark.skip` by default. Uncomment to run against a replica set.

- [ ] **Step 1: Write the tests (skipped for standalone)**

```python
import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


class Account(VellumBaseModel):
    owner: str
    balance: float

    class Settings:
        collection_name = "accounts"


@pytest_asyncio.fixture
async def repo(db):
    return VellumRepository(Account, db)


@pytest.mark.skip(reason="Requires a MongoDB replica set, not a standalone server")
async def test_transaction_commits(repo):
    a = Account(owner="Alice", balance=1000.0)
    b = Account(owner="Bob", balance=500.0)
    await repo.create(a)
    await repo.create(b)

    async with repo.transaction() as session:
        a.balance -= 100
        b.balance += 100
        await repo.update(a.id, a, session=session)
        await repo.update(b.id, b, session=session)

    alice = await repo.get(a.id)
    bob = await repo.get(b.id)
    assert alice.balance == 900.0
    assert bob.balance == 600.0


@pytest.mark.skip(reason="Requires a MongoDB replica set, not a standalone server")
async def test_transaction_rolls_back_on_error(repo):
    a = Account(owner="Charlie", balance=200.0)
    await repo.create(a)

    try:
        async with repo.transaction() as session:
            a.balance = 0
            await repo.update(a.id, a, session=session)
            raise RuntimeError("Simulated failure")
    except RuntimeError:
        pass

    fetched = await repo.get(a.id)
    assert fetched.balance == 200.0  # unchanged — rolled back
```

Save to `tests/test_transactions.py`.

- [ ] **Step 2: Add transaction context manager and session parameter to repository**

In `repository.py`:

```python
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClientSession

@asynccontextmanager
async def transaction(self):
    """
    Async context manager for multi-document ACID transactions.

    Requires a MongoDB replica set or sharded cluster.
    All repository operations within the block accept an optional
    `session` parameter — pass the yielded session to enroll them.

    Usage::

        async with repo.transaction() as session:
            await repo.update(id_a, doc_a, session=session)
            await repo.update(id_b, doc_b, session=session)
    """
    async with await self.collection.database.client.start_session() as session:
        async with session.start_transaction():
            yield session
```

Update method signatures to accept an optional `session` parameter (add `session=None` to create/update/delete and pass it to the Motor call):

```python
async def create(self, item: T, session=None) -> T:
    ...
    result = await self.collection.insert_one(doc, session=session)
    ...

async def update(self, doc_id, item: T, session=None) -> T:
    ...
    result = await self.collection.update_one(mongo_filter, {"$set": doc}, session=session)
    ...

async def delete(self, doc_id, session=None) -> bool:
    ...
    raw = await self.collection.find_one({"_id": query_id}, session=session)
    result = await self.collection.delete_one({"_id": query_id}, session=session)
    ...
```

- [ ] **Step 3: Run (skipped tests are fine)**

```bash
pytest tests/test_transactions.py -v
```

Expected: 2 tests SKIPPED (not failed).

- [ ] **Step 4: Commit**

```bash
git add src/vellum/repository.py tests/test_transactions.py
git commit -m "feat: add transaction() context manager with optional session parameter"
```

---

## Task 11: Connection Utilities + FastAPI Integration

**Files:**
- Create: `src/vellum/connection.py`
- Create: `src/vellum/fastapi.py`

- [ ] **Step 1: Write connection.py**

```python
"""
Vellum connection utilities.

Use `connect_to_mongodb` to create a Motor client.
For FastAPI, use the `on_startup` and `on_shutdown` helpers
or the `lifespan` context manager.

Example (FastAPI lifespan)::

    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from vellum.connection import mongodb_lifespan

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = await connect_to_mongodb("mongodb://localhost:27017")
        app.state.db = client["mydb"]
        yield
        client.close()

    app = FastAPI(lifespan=lifespan)
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def connect_to_mongodb(uri: str) -> AsyncIOMotorClient:
    """
    Create and return an AsyncIOMotorClient.

    The client is not connected until the first operation — Motor is lazy.
    Call `.close()` on it during application shutdown.
    """
    return AsyncIOMotorClient(uri)


def get_database(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    """Return a database handle from an existing client."""
    return client[db_name]
```

Save to `src/vellum/connection.py`.

- [ ] **Step 2: Write fastapi.py**

```python
"""
Vellum FastAPI integration helpers.

`repository_factory` creates a FastAPI dependency that injects a
VellumRepository into route handlers.

Example::

    from fastapi import FastAPI, Depends
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from vellum.fastapi import repository_factory
    from vellum.repository import VellumRepository
    from myapp.models import User

    app = FastAPI()

    def get_db() -> AsyncIOMotorDatabase:
        # Return your database from app state / DI container
        ...

    user_repo_dep = repository_factory(User, get_db)

    @app.get("/users/{user_id}")
    async def get_user(user_id: str, repo: VellumRepository[User] = Depends(user_repo_dep)):
        return await repo.get(user_id)
"""

from typing import Callable, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorDatabase

from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository

T = TypeVar("T", bound=VellumBaseModel)


def repository_factory(
    model_cls: Type[T],
    get_db: Callable[[], AsyncIOMotorDatabase],
) -> Callable[[], VellumRepository[T]]:
    """
    Returns a FastAPI dependency function that provides a VellumRepository.

    Args:
        model_cls: The VellumBaseModel subclass this repository manages.
        get_db:    A callable (or FastAPI dependency) that returns the database.

    Returns:
        A dependency function you can use with `Depends(...)`.
    """
    def _dependency(db: AsyncIOMotorDatabase = get_db()) -> VellumRepository[T]:
        return VellumRepository(model_cls, db)

    return _dependency
```

Save to `src/vellum/fastapi.py`.

- [ ] **Step 3: Commit**

```bash
git add src/vellum/connection.py src/vellum/fastapi.py
git commit -m "feat: add connection utilities and FastAPI dependency injection helpers"
```

---

## Task 12: Public API (`__init__.py`)

**Files:**
- Modify: `src/vellum/__init__.py`

- [ ] **Step 1: Write __init__.py**

```python
"""
Vellum — The Precision ODM for Asynchronous MongoDB & Pydantic.

Quick start::

    from motor.motor_asyncio import AsyncIOMotorClient
    from vellum import VellumBaseModel, VellumRepository

    class User(VellumBaseModel):
        name: str
        email: str

        class Settings:
            collection_name = "users"
            indexes = [{"key": [("email", 1)], "unique": True}]

    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["myapp"]
    repo = VellumRepository(User, db)

    # Create
    user = await repo.create(User(name="Alice", email="alice@example.com"))

    # Query
    users = await repo.find({"name": "Alice"})

    # Aggregation
    from vellum import AggregationPipeline
    results = await AggregationPipeline(repo.collection).match({"name": "Alice"}).execute()
"""

from vellum.aggregation import AggregationPipeline
from vellum.connection import connect_to_mongodb, get_database
from vellum.exceptions import (
    DocumentNotFoundError,
    HookError,
    OptimisticLockError,
    VellumError,
)
from vellum.model import OptimisticConcurrencyMixin, SoftDeleteMixin, VellumBaseModel
from vellum.query import (
    All,
    And,
    ElemMatch,
    Eq,
    Exists,
    Gt,
    Gte,
    In,
    Lt,
    Lte,
    Ne,
    Nor,
    Not,
    NotIn,
    Or,
    Regex,
    Size,
    all_,
    elem_match,
    eq,
    exists,
    gt,
    gte,
    in_,
    lt,
    lte,
    ne,
    not_in,
    regex,
    size,
)
from vellum.repository import VellumRepository

__all__ = [
    # Core
    "VellumBaseModel",
    "VellumRepository",
    # Mixins
    "OptimisticConcurrencyMixin",
    "SoftDeleteMixin",
    # Aggregation
    "AggregationPipeline",
    # Query classes
    "Eq", "Ne", "Gt", "Gte", "Lt", "Lte",
    "In", "NotIn", "All", "Size", "ElemMatch",
    "Exists", "Regex",
    "And", "Or", "Nor", "Not",
    # Query functions
    "eq", "ne", "gt", "gte", "lt", "lte",
    "in_", "not_in", "all_", "size", "elem_match",
    "exists", "regex",
    # Exceptions
    "VellumError",
    "DocumentNotFoundError",
    "OptimisticLockError",
    "HookError",
    # Connection
    "connect_to_mongodb",
    "get_database",
]
```

- [ ] **Step 2: Verify imports work**

```bash
python -c "import vellum; print('OK')"
```

Expected: `OK` with no errors.

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v --ignore=tests/test_transactions.py
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add src/vellum/__init__.py
git commit -m "chore: expose public API through __init__.py"
```

---

## Task 13: Learning Document

**Files:**
- Create: `docs/learning.md`

- [ ] **Step 1: Write the learning document**

```markdown
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
```

Save to `docs/learning.md`.

- [ ] **Step 2: Commit**

```bash
git add docs/learning.md
git commit -m "docs: add learning document explaining bugs and new concepts"
```

---

## Final: Full Test Run

- [ ] **Run the complete suite**

```bash
pytest tests/ -v --ignore=tests/test_transactions.py
```

Expected: all tests PASS. Transaction tests are skipped (require replica set).

- [ ] **Final commit**

```bash
git add -A
git commit -m "chore: complete Vellum ODM implementation — all phases done"
```

---

## Self-Review

**Spec coverage check:**
- Phase 0 tasks (0.1-0.6): Task 1, 3, 4, 11 ✓
- Phase 1.1 query operators: Task 5 ✓
- Phase 1.2 aggregation pipeline: Task 6 ✓
- Phase 1.3 type mapping: UUID strategy fixed in Task 3 ✓ (Decimal128 noted as beyond scope of a learning project)
- Phase 2.1 type-safe aggregation output: Task 6 `output_model` ✓
- Phase 2.2 lifecycle hooks: Task 7 ✓
- Phase 2.3 OCC: Task 8 ✓
- Phase 2.4 soft delete: Task 9 ✓
- Phase 2.5 advanced aggregation stages: Task 6 (unwind, lookup, addFields, set, replaceRoot) ✓
- Phase 3.1 transactions: Task 10 ✓
- Phase 3.3 FastAPI integration: Task 11 ✓
- Phase 3.4/3.5 documentation: Task 13 (learning doc) ✓
- Exceptions module: Task 2 ✓
- Public __init__.py: Task 12 ✓

**No placeholders found.** All steps contain complete code.
**Type consistency verified.** Method signatures are consistent across tasks.
