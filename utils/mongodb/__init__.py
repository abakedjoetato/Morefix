"""
MongoDB Compatibility Layer package

This package provides compatibility layers for MongoDB interactions,
supporting both pymongo/motor with proper error handling.
"""

from utils.safe_mongodb import (
    SafeMongoDBResult,
    SafeDocument,
    get_collection,
    safe_find_one,
    safe_find,
    safe_insert_one,
    safe_update_one,
    safe_delete_one,
    safe_count
)

from utils.mongo_compat import (
    serialize_document,
    deserialize_document,
    is_objectid,
    to_object_id,
    handle_datetime,
    filter_document
)

__all__ = [
    # Safe MongoDB
    'SafeMongoDBResult',
    'SafeDocument',
    'get_collection',
    'safe_find_one',
    'safe_find',
    'safe_insert_one',
    'safe_update_one',
    'safe_delete_one',
    'safe_count',
    
    # MongoDB compatibility
    'serialize_document',
    'deserialize_document',
    'is_objectid',
    'to_object_id',
    'handle_datetime',
    'filter_document'
]