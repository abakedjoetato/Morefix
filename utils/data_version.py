"""
Data Version Tracking for Tower of Temptation PvP Statistics Bot

This module provides tracking for data formats and migrations:
1. Database schema version detection
2. Collection-specific version tracking
3. Version comparison utilities
4. Migration requirements analysis

This ensures safe upgrades and backward compatibility.
"""
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union, Any
from datetime import datetime

# Setup logger
logger = logging.getLogger(__name__)

# Current schema versions
CURRENT_VERSIONS = {
    "guild_config": "1.0.0",
    "user_profiles": "1.0.0",
    "canvas_data": "1.0.0",
    "stats": "1.0.0",
    "errors": "1.0.0",
    "settings": "1.0.0"
}

# Migration functions registry
_MIGRATIONS = {}

# Version parsing utilities
def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a semantic version string
    
    Args:
        version_str: Version string to parse (e.g. "1.0.0")
        
    Returns:
        Tuple of (major, minor, patch) version numbers
        
    Raises:
        ValueError: If version string is invalid
    """
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', version_str)
    if not match:
        raise ValueError(f"Invalid version string: {version_str}")
    
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    
    return (major, minor, patch)

def compare_versions(version1: str, version2: str) -> int:
    """Compare two semantic version strings
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
        
    Raises:
        ValueError: If either version string is invalid
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0

def version_greater_or_equal(version1: str, version2: str) -> bool:
    """Check if version1 is greater than or equal to version2
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        True if version1 >= version2
    """
    return compare_versions(version1, version2) >= 0

def get_migration_path(from_version: str, to_version: str, collection: str) -> List[str]:
    """Get a sequence of migration steps from one version to another
    
    Args:
        from_version: Starting version
        to_version: Target version
        collection: Collection name
        
    Returns:
        List of intermediate versions to apply in sequence
    """
    if from_version == to_version:
        return []
    
    if collection not in _MIGRATIONS:
        return []
    
    # Get all available migrations for the collection
    migrations = _MIGRATIONS[collection]
    
    # Parse versions
    from_v = parse_version(from_version)
    to_v = parse_version(to_version)
    
    # Going backwards is not supported
    if from_v > to_v:
        logger.warning(f"Downgrading from {from_version} to {to_version} is not supported")
        return []
    
    # Find all applicable migrations
    steps = []
    current = from_version
    
    while compare_versions(current, to_version) < 0:
        # Find the next migration step
        next_version = None
        
        for v in migrations.keys():
            v_parsed = parse_version(v)
            
            # If this version is greater than current but less than or equal to target
            if (parse_version(current) < v_parsed <= to_v and 
                (next_version is None or parse_version(next_version) > v_parsed)):
                next_version = v
        
        if next_version is None:
            # No migration path available
            logger.warning(f"No migration path from {current} to {to_version} for {collection}")
            break
        
        steps.append(next_version)
        current = next_version
    
    return steps

# Version management class
class DataVersionManager:
    """Manager for data schema versions"""
    
    def __init__(self, db=None):
        """Initialize data version manager
        
        Args:
            db: Database instance for storing schema information
        """
        self.db = db
        self._cache = {}
    
    async def get_collection_version(self, collection: str) -> str:
        """Get the current version of a collection
        
        Args:
            collection: Collection name
            
        Returns:
            Version string, or "0.0.0" if not found
        """
        if not self.db:
            return "0.0.0"
        
        # Check cache first
        if collection in self._cache:
            return self._cache[collection]
        
        try:
            # Get version document from settings collection
            settings_collection = self.db.settings
            version_doc = await settings_collection.find_one({"_id": f"version:{collection}"})
            
            if version_doc and "version" in version_doc:
                version = version_doc["version"]
                # Update cache
                self._cache[collection] = version
                return version
            
            # No version found
            return "0.0.0"
        except Exception as e:
            logger.error(f"Error retrieving version for {collection}: {e}")
            return "0.0.0"
    
    async def set_collection_version(self, collection: str, version: str) -> bool:
        """Set the version of a collection
        
        Args:
            collection: Collection name
            version: Version string
            
        Returns:
            True if successful
        """
        if not self.db:
            return False
        
        try:
            # Update version document in settings collection
            settings_collection = self.db.settings
            await settings_collection.update_one(
                {"_id": f"version:{collection}"},
                {"$set": {
                    "version": version,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            
            # Update cache
            self._cache[collection] = version
            
            return True
        except Exception as e:
            logger.error(f"Error setting version for {collection}: {e}")
            return False
    
    async def get_all_versions(self) -> Dict[str, str]:
        """Get versions for all collections
        
        Returns:
            Dictionary mapping collection names to versions
        """
        if not self.db:
            return {}
        
        try:
            # Get all version documents from settings collection
            settings_collection = self.db.settings
            cursor = settings_collection.find({"_id": {"$regex": "^version:"}})
            
            versions = {}
            async for doc in cursor:
                collection = doc["_id"].split(":", 1)[1]
                versions[collection] = doc["version"]
            
            return versions
        except Exception as e:
            logger.error(f"Error retrieving all versions: {e}")
            return {}
    
    async def check_needs_migration(self, collection: str) -> bool:
        """Check if a collection needs migration
        
        Args:
            collection: Collection name
            
        Returns:
            True if migration is needed
        """
        if collection not in CURRENT_VERSIONS:
            return False
        
        current_version = await self.get_collection_version(collection)
        target_version = CURRENT_VERSIONS[collection]
        
        return compare_versions(current_version, target_version) < 0
    
    async def analyze_migration_needs(self) -> Dict[str, Dict[str, Any]]:
        """Analyze which collections need migration
        
        Returns:
            Dictionary with migration analysis
        """
        result = {}
        
        for collection, target_version in CURRENT_VERSIONS.items():
            current_version = await self.get_collection_version(collection)
            
            if compare_versions(current_version, target_version) < 0:
                # Collection needs migration
                migration_path = get_migration_path(current_version, target_version, collection)
                
                result[collection] = {
                    "current_version": current_version,
                    "target_version": target_version,
                    "needs_migration": True,
                    "migration_path": migration_path,
                    "can_migrate": len(migration_path) > 0
                }
            else:
                # Collection is up to date
                result[collection] = {
                    "current_version": current_version,
                    "target_version": target_version,
                    "needs_migration": False,
                    "migration_path": [],
                    "can_migrate": True
                }
        
        return result

# Migration registration
def register_migration(collection: str, target_version: str, migration_func: Any) -> None:
    """Register a migration function for a collection and version
    
    Args:
        collection: Collection name
        target_version: Target version for this migration
        migration_func: Async function to perform migration
    """
    global _MIGRATIONS
    
    if collection not in _MIGRATIONS:
        _MIGRATIONS[collection] = {}
    
    _MIGRATIONS[collection][target_version] = migration_func
    
    logger.info(f"Registered migration for {collection} to version {target_version}")

def get_migration_function(collection: str, target_version: str) -> Optional[Any]:
    """Get migration function for a collection and version
    
    Args:
        collection: Collection name
        target_version: Target version
        
    Returns:
        Migration function or None if not found
    """
    if collection not in _MIGRATIONS:
        return None
    
    return _MIGRATIONS[collection].get(target_version)

# Setup function
async def initialize_version_manager(db) -> DataVersionManager:
    """Initialize the version manager with the database
    
    Args:
        db: Database instance
        
    Returns:
        DataVersionManager instance
    """
    manager = DataVersionManager(db)
    
    # Ensure settings collection exists
    try:
        await db.settings.find_one({"_id": "version_manager_initialized"})
    except Exception:
        # Collection doesn't exist, create it
        try:
            await db.create_collection("settings")
        except Exception:
            # Collection might already exist
            pass
    
    # Initialize default versions if needed
    for collection, version in CURRENT_VERSIONS.items():
        current = await manager.get_collection_version(collection)
        if current == "0.0.0":
            # Check if the collection exists and has data
            try:
                count = await db[collection].count_documents({})
                if count > 0:
                    # Collection exists with data, assume it's the current version
                    await manager.set_collection_version(collection, version)
                    logger.info(f"Initialized version for existing {collection} collection: {version}")
                else:
                    # Collection is empty or doesn't exist, just set the version
                    await manager.set_collection_version(collection, version)
                    logger.info(f"Initialized version for new {collection} collection: {version}")
            except Exception as e:
                logger.error(f"Error checking collection {collection}: {e}")
    
    # Mark as initialized
    await db.settings.update_one(
        {"_id": "version_manager_initialized"},
        {"$set": {
            "initialized_at": datetime.utcnow(),
            "current_versions": CURRENT_VERSIONS
        }},
        upsert=True
    )
    
    return manager