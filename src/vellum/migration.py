from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


@dataclass
class MigrationRecord:
    version: int
    name: str
    applied_at: str | None = None


class Migration(ABC):
    version: int
    name: str

    @abstractmethod
    async def up(self, db: AsyncIOMotorDatabase) -> None: ...

    @abstractmethod
    async def down(self, db: AsyncIOMotorDatabase) -> None: ...


class SimpleMigration(Migration):
    def __init__(
        self,
        version: int,
        name: str,
        up_fn: Callable[[AsyncIOMotorDatabase], Any],
        down_fn: Callable[[AsyncIOMotorDatabase], Any],
    ) -> None:
        self.version = version
        self.name = name
        self._up_fn = up_fn
        self._down_fn = down_fn

    async def up(self, db: AsyncIOMotorDatabase) -> None:
        await self._up_fn(db)

    async def down(self, db: AsyncIOMotorDatabase) -> None:
        await self._down_fn(db)


class MigrationRunner:

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        self._collection = db["_migrations"]

    async def _ensure_collection(self) -> None:
        exists = await self._collection.find_one(session=None)
        if exists is None:
            await self._collection.insert_one({
                "_id": "migrations",
                "applied": [],
            })

    async def get_applied(self) -> list[MigrationRecord]:
        rec = await self._collection.find_one({"_id": "migrations"})
        if rec is None:
            return []
        return [MigrationRecord(**m) for m in rec.get("applied", [])]

    async def run(self, migrations: list[Migration]) -> list[MigrationRecord]:
        applied = await self.get_applied()
        applied_versions = {m.version for m in applied}
        pending = sorted(
            [m for m in migrations if m.version not in applied_versions],
            key=lambda m: m.version,
        )
        results: list[MigrationRecord] = []
        for migration in pending:
            await migration.up(self._db)
            rec = MigrationRecord(version=migration.version, name=migration.name)
            results.append(rec)
            await self._collection.update_one(
                {"_id": "migrations"},
                {"$push": {"applied": {"version": rec.version, "name": rec.name}}},
                upsert=True,
            )
        return results

    async def rollback(self, migrations: list[Migration], steps: int = 1) -> list[MigrationRecord]:
        applied = await self.get_applied()
        if not applied:
            return []
        to_rollback = applied[-steps:]
        version_map = {m.version: m for m in migrations}
        results: list[MigrationRecord] = []
        for rec in reversed(to_rollback):
            migration = version_map.get(rec.version)
            if migration is not None:
                await migration.down(self._db)
            results.append(rec)
            await self._collection.update_one(
                {"_id": "migrations"},
                {"$pull": {"applied": {"version": rec.version}}},
            )
        return results

    async def pending(self, migrations: list[Migration]) -> list[Migration]:
        applied = await self.get_applied()
        applied_versions = {m.version for m in applied}
        return sorted(
            [m for m in migrations if m.version not in applied_versions],
            key=lambda m: m.version,
        )

    async def status(self, migrations: list[Migration]) -> dict[str, Any]:
        applied = await self.get_applied()
        applied_versions = {m.version for m in applied}
        rows = []
        for m in sorted(migrations, key=lambda x: x.version):
            rows.append({
                "version": m.version,
                "name": m.name,
                "applied": m.version in applied_versions,
            })
        return {
            "total": len(migrations),
            "applied": len(applied),
            "pending": len(migrations) - len(applied),
            "migrations": rows,
        }
