from __future__ import annotations

import pytest

from vellum.migration import MigrationRunner, SimpleMigration


@pytest.fixture
async def runner(db):
    return MigrationRunner(db)


@pytest.mark.asyncio
async def test_run_applies_pending_migrations(runner):
    calls = []

    async def up1(db):
        calls.append("up1")

    async def down1(db):
        calls.append("down1")

    async def up2(db):
        calls.append("up2")

    async def down2(db):
        calls.append("down2")

    m1 = SimpleMigration(1, "first", up1, down1)
    m2 = SimpleMigration(2, "second", up2, down2)

    result = await runner.run([m1, m2])
    assert len(result) == 2
    assert calls == ["up1", "up2"]


@pytest.mark.asyncio
async def test_run_skips_already_applied(runner):
    calls = []

    async def up1(db):
        calls.append("up1")

    async def down1(db):
        calls.append("down1")

    m1 = SimpleMigration(1, "first", up1, down1)
    await runner.run([m1])
    result = await runner.run([m1])
    assert len(result) == 0
    assert calls == ["up1"]


@pytest.mark.asyncio
async def test_rollback_reverses_last_migration(runner):
    calls = []

    async def up1(db):
        calls.append("up1")

    async def down1(db):
        calls.append("down1")

    m1 = SimpleMigration(1, "first", up1, down1)
    await runner.run([m1])
    rolled = await runner.rollback([m1])
    assert len(rolled) == 1
    assert calls == ["up1", "down1"]


@pytest.mark.asyncio
async def test_status_reports_correctly(runner):
    async def up1(db):
        pass

    async def down1(db):
        pass

    m1 = SimpleMigration(1, "first", up1, down1)
    m2 = SimpleMigration(2, "second", up1, down1)
    await runner.run([m1])
    status = await runner.status([m1, m2])
    assert status["total"] == 2
    assert status["applied"] == 1
    assert status["pending"] == 1


@pytest.mark.asyncio
async def test_pending_returns_only_unapplied(runner):
    async def up1(db):
        pass

    async def down1(db):
        pass

    m1 = SimpleMigration(1, "first", up1, down1)
    m2 = SimpleMigration(2, "second", up1, down1)
    await runner.run([m1])
    pending = await runner.pending([m1, m2])
    assert len(pending) == 1
    assert pending[0].version == 2


@pytest.mark.asyncio
async def test_rollback_steps(runner):
    calls = []

    async def mk_up(n):
        async def up(db):
            calls.append(f"up{n}")

        return up

    async def mk_down(n):
        async def down(db):
            calls.append(f"down{n}")

        return down

    migrations = [
        SimpleMigration(1, "first", await mk_up(1), await mk_down(1)),
        SimpleMigration(2, "second", await mk_up(2), await mk_down(2)),
        SimpleMigration(3, "third", await mk_up(3), await mk_down(3)),
    ]
    await runner.run(migrations)
    rolled = await runner.rollback(migrations, steps=2)
    assert len(rolled) == 2
    assert calls == ["up1", "up2", "up3", "down3", "down2"]
