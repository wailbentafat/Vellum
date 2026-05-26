import pytest
import pytest_asyncio

from vellum.exceptions import DocumentNotFoundError
from vellum.model import SoftDeleteMixin, VellumBaseModel
from vellum.repository import VellumRepository


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
