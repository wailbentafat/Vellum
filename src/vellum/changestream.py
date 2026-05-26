from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorChangeStream

from vellum.model import VellumBaseModel

ChangeHandler = Callable[..., None]


@dataclass
class ChangeEvent[T]:
    operation_type: str
    doc_id: UUID | str | None
    full_document: dict[str, Any] | None
    model: T | None
    raw: dict[str, Any]


class ChangeStream[T: VellumBaseModel]:

    def __init__(
        self,
        model_cls: type[T],
        stream: AsyncIOMotorChangeStream,
    ) -> None:
        self._model_cls = model_cls
        self._stream = stream
        self._handlers: dict[str, list[ChangeHandler]] = {}
        self._task: asyncio.Task[None] | None = None

    def on(self, event_type: str, handler: ChangeHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def _notify(self, event: ChangeEvent[T]) -> None:
        handlers = self._handlers.get(event.operation_type, [])
        all_handlers = self._handlers.get("*", [])
        for h in handlers + all_handlers:
            h(event)

    def _parse_event(self, raw: dict[str, Any]) -> ChangeEvent[T]:
        op = raw.get("operationType", "unknown")
        doc_id = None
        full_doc = raw.get("fullDocument")
        model = None

        doc_key = raw.get("documentKey", {})
        if doc_key:
            rid = doc_key.get("_id")
            doc_id = UUID(rid) if rid and isinstance(rid, str) else rid

        if full_doc:
            try:
                model = self._model_cls.from_mongo(full_doc)
            except Exception:
                pass

        return ChangeEvent(
            operation_type=op,
            doc_id=doc_id,
            full_document=full_doc,
            model=model,
            raw=raw,
        )

    async def _run(self) -> None:
        try:
            async for change in self._stream:
                event = self._parse_event(change)
                self._notify(event)
        except asyncio.CancelledError:
            pass

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._stream.close()

    def __aiter__(self) -> AsyncGenerator[ChangeEvent[T], None]:
        return self._async_generator()

    async def _async_generator(self) -> AsyncGenerator[ChangeEvent[T], None]:
        async for change in self._stream:
            event = self._parse_event(change)
            yield event
