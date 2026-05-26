from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


def connect_to_mongodb(uri: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(uri)


def get_database(client: AsyncIOMotorClient, db_name: str) -> AsyncIOMotorDatabase:
    return client[db_name]
