from pymongo import MongoClient
from pymongo.database import Database

from .constants import FA_DB_NAME, FA_MONGO_URI


# Function to establish MongoDB connection and return db, collection objects
def get_mongo_connection(uri: str, database_name: str) -> Database:
    client = MongoClient(uri)
    db = client[database_name]
    return db


# Dependency function to inject MongoDB connection
def get_fa_connection():

    db_conn = get_mongo_connection(FA_MONGO_URI, FA_DB_NAME)
    return db_conn
