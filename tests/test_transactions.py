import pytest
import pytest_asyncio

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
    assert fetched.balance == 200.0
