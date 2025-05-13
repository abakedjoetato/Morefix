"""
MongoDB Schema Definitions for Tower of Temptation PvP Statistics Bot

This module defines the schemas for MongoDB collections:
1. Document structure validation
2. Field definitions and types
3. Default values and constraints
4. Relationship definitions

Consistent schema definitions ensure data integrity and compatibility.
"""
import logging
from typing import Dict, Any, List, Optional, Union
import json

# Configure module-specific logger
logger = logging.getLogger(__name__)

# Error telemetry schema
ERROR_TELEMETRY_SCHEMA = {
    "bsonType": "object",
    "required": ["fingerprint", "category", "error_type", "first_seen", "last_seen", "occurrence_count"],
    "properties": {
        "fingerprint": {
            "bsonType": "string",
            "description": "Unique identifier for this error pattern"
        },
        "category": {
            "bsonType": "string",
            "description": "Error category (discord_api, database, sftp, etc.)"
        },
        "error_type": {
            "bsonType": "string",
            "description": "Exception type or error class name"
        },
        "error_message": {
            "bsonType": "string",
            "description": "Error message text"
        },
        "normalized_message": {
            "bsonType": "string",
            "description": "Normalized error message with variables removed"
        },
        "first_seen": {
            "bsonType": "date",
            "description": "When this error was first encountered"
        },
        "last_seen": {
            "bsonType": "date",
            "description": "When this error was most recently encountered"
        },
        "occurrence_count": {
            "bsonType": "int",
            "minimum": 1,
            "description": "Number of times this error has occurred"
        },
        "last_error_id": {
            "bsonType": "string",
            "description": "ID of the most recent error occurrence"
        },
        "last_message": {
            "bsonType": "string",
            "description": "Message from the most recent error occurrence"
        },
        "last_traceback": {
            "bsonType": "string",
            "description": "Stack trace from the most recent error occurrence"
        },
        "last_context": {
            "bsonType": "object",
            "description": "Context data from the most recent error occurrence"
        },
        "recent_occurrences": {
            "bsonType": "array",
            "description": "Recent occurrences of this error",
            "items": {
                "bsonType": "object",
                "required": ["timestamp", "error_id"],
                "properties": {
                    "timestamp": {
                        "bsonType": "date",
                        "description": "When this occurrence happened"
                    },
                    "error_id": {
                        "bsonType": "string",
                        "description": "Unique ID for this error occurrence"
                    },
                    "context": {
                        "bsonType": "object",
                        "description": "Context data for this occurrence"
                    }
                }
            }
        }
    }
}

# Guild schema
GUILD_SCHEMA = {
    "bsonType": "object",
    "required": ["guild_id"],
    "properties": {
        "guild_id": {
            "bsonType": "string",
            "description": "Discord guild ID"
        },
        "name": {
            "bsonType": "string",
            "description": "Guild name"
        },
        "owner_id": {
            "bsonType": "string",
            "description": "Guild owner's Discord ID"
        },
        "premium_tier": {
            "bsonType": "int",
            "minimum": 0,
            "maximum": 3,
            "description": "Premium tier level (0-3)"
        },
        "joined_at": {
            "bsonType": "date",
            "description": "When the bot joined this guild"
        },
        "settings": {
            "bsonType": "object",
            "description": "Guild-specific settings"
        },
        "servers": {
            "bsonType": "object",
            "description": "SFTP servers configured for this guild",
            "patternProperties": {
                ".*": {
                    "bsonType": "object",
                    "properties": {
                        "name": {
                            "bsonType": "string",
                            "description": "Server display name"
                        },
                        "hostname": {
                            "bsonType": "string",
                            "description": "SFTP hostname"
                        },
                        "port": {
                            "bsonType": ["int", "string"],
                            "description": "SFTP port"
                        },
                        "username": {
                            "bsonType": "string",
                            "description": "SFTP username"
                        },
                        "password": {
                            "bsonType": "string",
                            "description": "SFTP password (should be encrypted in production)"
                        },
                        "log_paths": {
                            "bsonType": "array",
                            "description": "Paths to search for logs",
                            "items": {
                                "bsonType": "string"
                            }
                        },
                        "enabled": {
                            "bsonType": "bool",
                            "description": "Whether this server is enabled"
                        }
                    }
                }
            }
        }
    }
}

# Premium subscription schema
PREMIUM_SCHEMA = {
    "bsonType": "object",
    "required": ["guild_id", "tier", "active"],
    "properties": {
        "guild_id": {
            "bsonType": "string",
            "description": "Discord guild ID"
        },
        "tier": {
            "bsonType": "int",
            "minimum": 1,
            "maximum": 3,
            "description": "Premium tier level (1-3)"
        },
        "active": {
            "bsonType": "bool",
            "description": "Whether the subscription is currently active"
        },
        "since": {
            "bsonType": "date",
            "description": "When the subscription started"
        },
        "until": {
            "bsonType": "date",
            "description": "When the subscription expires"
        },
        "payment_id": {
            "bsonType": "string",
            "description": "Payment reference ID"
        },
        "features": {
            "bsonType": "array",
            "description": "List of enabled premium features",
            "items": {
                "bsonType": "string"
            }
        }
    }
}

# Server configuration schema (separate from guild settings)
SERVER_SCHEMA = {
    "bsonType": "object",
    "required": ["server_id", "guild_id"],
    "properties": {
        "server_id": {
            "bsonType": "string",
            "description": "Unique server identifier"
        },
        "guild_id": {
            "bsonType": "string",
            "description": "Discord guild ID this server belongs to"
        },
        "name": {
            "bsonType": "string",
            "description": "Server display name"
        },
        "hostname": {
            "bsonType": "string",
            "description": "SFTP hostname"
        },
        "port": {
            "bsonType": ["int", "string"],
            "description": "SFTP port"
        },
        "username": {
            "bsonType": "string",
            "description": "SFTP username"
        },
        "password": {
            "bsonType": "string",
            "description": "SFTP password (should be encrypted in production)"
        },
        "log_paths": {
            "bsonType": "array",
            "description": "Paths to search for logs",
            "items": {
                "bsonType": "string"
            }
        },
        "enabled": {
            "bsonType": "bool",
            "description": "Whether this server is enabled"
        },
        "last_connected": {
            "bsonType": "date",
            "description": "When we last successfully connected to this server"
        },
        "connection_errors": {
            "bsonType": "int",
            "description": "Count of consecutive connection errors"
        }
    }
}

# Dictionary mapping collection names to schemas
COLLECTION_SCHEMAS = {
    "errors": ERROR_TELEMETRY_SCHEMA,
    "guilds": GUILD_SCHEMA,
    "premium": PREMIUM_SCHEMA,
    "servers": SERVER_SCHEMA
}

async def ensure_schemas(db):
    """Ensure that all collections have the correct schemas
    
    Args:
        db: MongoDB database instance
    
    Returns:
        bool: True if schemas were created successfully
    """
    try:
        # Get list of existing collections
        existing_collections = await db.list_collection_names()
        
        # Create or update each collection with its schema
        for collection_name, schema in COLLECTION_SCHEMAS.items():
            schema_validator = {
                "$jsonSchema": schema
            }
            
            if collection_name in existing_collections:
                # Update existing collection
                await db.command({
                    "collMod": collection_name,
                    "validator": schema_validator,
                    "validationLevel": "moderate"
                })
                logger.debug(f"Updated schema for collection: {collection_name}")
            else:
                # Create new collection
                await db.create_collection(
                    collection_name,
                    validator=schema_validator
                )
                
                # Create indexes
                if collection_name == "errors":
                    await db[collection_name].create_index("fingerprint", unique=True)
                    await db[collection_name].create_index("category")
                    await db[collection_name].create_index("last_seen")
                elif collection_name == "guilds":
                    await db[collection_name].create_index("guild_id", unique=True)
                elif collection_name == "premium":
                    await db[collection_name].create_index("guild_id", unique=True)
                elif collection_name == "servers":
                    await db[collection_name].create_index("server_id", unique=True)
                    await db[collection_name].create_index("guild_id")
                
                logger.info(f"Created collection with schema: {collection_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring database schemas: {e}")
        return False