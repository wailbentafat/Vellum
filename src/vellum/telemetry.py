from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from vellum.repository import VellumRepository


class NoopTracer:
    def start_span(self, name: str) -> NoopSpan:
        return NoopSpan()


class NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def record_exception(self, exc: Exception) -> None:
        pass

    def __enter__(self) -> NoopSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


noop_tracer = NoopTracer()


class TracedRepository[T]:

    def __init__(
        self,
        repo: VellumRepository[T],
        tracer: Any = None,
    ) -> None:
        self._repo = repo
        self._tracer = tracer or noop_tracer

    @property
    def collection(self):
        return self._repo.collection

    @property
    def model_cls(self):
        return self._repo.model_cls

    async def get(self, doc_id: UUID | str, **kwargs: Any) -> T:
        with self._tracer.start_span("repository.get") as span:
            span.set_attribute("model", self._repo.model_cls.__name__)
            span.set_attribute("doc_id", str(doc_id))
            start = time.monotonic()
            try:
                result = await self._repo.get(doc_id, **kwargs)
                span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
                return result
            except Exception as e:
                span.record_exception(e)
                raise

    async def create(self, item: T, **kwargs: Any) -> T:
        with self._tracer.start_span("repository.create") as span:
            span.set_attribute("model", self._repo.model_cls.__name__)
            start = time.monotonic()
            try:
                result = await self._repo.create(item, **kwargs)
                span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
                span.set_attribute("doc_id", str(result.id))
                return result
            except Exception as e:
                span.record_exception(e)
                raise

    async def update(self, doc_id: UUID | str, item: T, **kwargs: Any) -> T:
        with self._tracer.start_span("repository.update") as span:
            span.set_attribute("model", self._repo.model_cls.__name__)
            span.set_attribute("doc_id", str(doc_id))
            start = time.monotonic()
            try:
                result = await self._repo.update(doc_id, item, **kwargs)
                span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
                return result
            except Exception as e:
                span.record_exception(e)
                raise

    async def delete(self, doc_id: UUID | str, **kwargs: Any) -> bool:
        with self._tracer.start_span("repository.delete") as span:
            span.set_attribute("model", self._repo.model_cls.__name__)
            span.set_attribute("doc_id", str(doc_id))
            start = time.monotonic()
            try:
                result = await self._repo.delete(doc_id, **kwargs)
                span.set_attribute("duration_ms", (time.monotonic() - start) * 1000)
                return result
            except Exception as e:
                span.record_exception(e)
                raise

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repo, name)
