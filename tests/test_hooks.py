import pytest
import pytest_asyncio
from vellum.model import VellumBaseModel
from vellum.repository import VellumRepository


delete_hook_log: list[str] = []


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
    global delete_hook_log
    delete_hook_log = []

    class TrackedDeleteItem(VellumBaseModel):
        name: str

        class Settings:
            collection_name = "tracked_delete"

        async def before_delete(self) -> None:
            delete_hook_log.append("before_delete")

        async def after_delete(self) -> None:
            delete_hook_log.append("after_delete")

    tracked_repo = VellumRepository(TrackedDeleteItem, repo.collection.database)
    item = TrackedDeleteItem(name="delete-test")
    await tracked_repo.create(item)
    await tracked_repo.delete(item.id)
    assert "before_delete" in delete_hook_log
    assert "after_delete" in delete_hook_log


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
