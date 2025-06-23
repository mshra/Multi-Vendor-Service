from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import ServerSelectionTimeoutError
from app.logger import log
from .config import settings

client: AsyncMongoClient | None = None
db: AsyncDatabase | None = None
collection: AsyncCollection | None = None


async def start_mongo():
    global client, db, collection

    try:
        client = AsyncMongoClient(settings.MONGO_URL)
        db = client.jobs
        collection = db.jobs

        log.info("MongoDB connection established successfully")
    except ServerSelectionTimeoutError as e:
        log.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        log.error(f"Unexpected error connecting to MongoDB: {e}")
        raise


async def close_mongo():
    global client
    if client:
        await client.close()
        log.info("MongoDB connection closed")


def get_collection() -> AsyncCollection:
    if collection is None:
        raise RuntimeError("MongoDB not initialized")

    return collection
