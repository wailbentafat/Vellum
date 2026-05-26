from __future__ import annotations

from typing import Any
from uuid import UUID

from vellum.repository import VellumRepository


class InMemoryCache:
    def __init__(self, ttl: int = 60) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        import time

        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        import time

        self._store[key] = (time.monotonic(), value)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


class CachedRepository[T]:

    def __init__(
        self,
        repo: VellumRepository[T],
        cache: Any | None = None,
        ttl: int = 60,
    ) -> None:
        self._repo = repo
        self._cache = cache or InMemoryCache(ttl=ttl)

    @property
    def collection(self):
        return self._repo.collection

    @property
    def model_cls(self):
        return self._repo.model_cls

    def _make_key(self, prefix: str, *parts: str) -> str:
        return f"{prefix}:{':'.join(parts)}"

    async def get(self, doc_id: UUID | str, include_deleted: bool = False) -> T:
        key = self._make_key("get", str(doc_id))
        cached = self._cache.get(key)
        if cached is not None:
            return self._repo.model_cls.from_mongo(cached)
        item = await self._repo.get(doc_id, include_deleted)
        self._cache.set(key, item.to_mongo())
        return item

    async def create(self, item: T, **kwargs: Any) -> T:
        result = await self._repo.create(item, **kwargs)
        self._cache.set(self._make_key("get", str(result.id)), result.to_mongo())
        return result

    async def update(self, doc_id: UUID | str, item: T, **kwargs: Any) -> T:
        result = await self._repo.update(doc_id, item, **kwargs)
        self._cache.set(self._make_key("get", str(doc_id)), result.to_mongo())
        return result

    async def delete(self, doc_id: UUID | str, **kwargs: Any) -> bool:
        result = await self._repo.delete(doc_id, **kwargs)
        self._cache.delete(self._make_key("get", str(doc_id)))
        return result

    def invalidate(self, doc_id: UUID | str) -> None:
        self._cache.delete(self._make_key("get", str(doc_id)))

    def clear_cache(self) -> None:
        self._cache.clear()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repo, name)
