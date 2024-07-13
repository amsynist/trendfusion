from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

from ..constants import FA_DB_NAME, FA_MONGO_URI


async def get_mongo_connection(uri: str, database_name: str) -> AsyncIOMotorDatabase:
    client = AsyncIOMotorClient(uri, server_api=ServerApi("1"))
    db = client[database_name]
    return db


async def get_fa_connection():
    db_conn = await get_mongo_connection(FA_MONGO_URI, FA_DB_NAME)
    return db_conn
