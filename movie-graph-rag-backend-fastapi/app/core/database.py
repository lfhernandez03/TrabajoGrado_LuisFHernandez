from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

_client: MongoClient | None = None
_database: Database | None = None


def connect_to_mongo() -> None:
    global _client, _database
    _client = MongoClient(settings.mongo_uri)
    db_name = settings.mongo_uri.rsplit("/", 1)[-1].split("?")[0] or "movie-graph-rag"
    _database = _client[db_name]


def close_mongo_connection() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None


def get_database() -> Database:
    if _database is None:
        raise RuntimeError("MongoDB is not connected")
    return _database


def ping_mongo() -> bool:
    if _client is None:
        return False
    try:
        _client.admin.command("ping")
        return True
    except Exception:
        return False
