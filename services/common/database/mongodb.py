"""MongoDB connection handling."""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo(mongo_uri: str, database_name: str) -> None:
    """
    Connect to MongoDB.

    Args:
        mongo_uri: MongoDB connection URI
        database_name: Name of the database to use
    """
    global _client, _database

    logger.info(f"Connecting to MongoDB at {mongo_uri}")
    _client = AsyncIOMotorClient(mongo_uri)
    _database = _client[database_name]

    # Test connection
    await _client.admin.command('ping')
    logger.info(f"Successfully connected to MongoDB database: {database_name}")


async def close_database_connection() -> None:
    """Close MongoDB connection."""
    global _client, _database

    if _client:
        logger.info("Closing MongoDB connection")
        _client.close()
        _client = None
        _database = None


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the MongoDB database instance.

    Returns:
        AsyncIOMotorDatabase: The database instance

    Raises:
        RuntimeError: If database is not connected
    """
    if _database is None:
        raise RuntimeError("Database is not connected. Call connect_to_mongo first.")
    return _database
