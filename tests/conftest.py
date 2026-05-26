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
