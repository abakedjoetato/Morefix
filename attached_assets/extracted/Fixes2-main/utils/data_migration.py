"""
Data Migration Utilities for Tower of Temptation PvP Statistics Bot

This module provides data migration functionality:
1. Schema migrations with versioning
2. Data format conversions
3. Collection upgrades
4. Database integrity verification

This ensures safe data evolution without breaking changes.
"""
import logging
import asyncio
import json
import copy
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime

from utils.data_version import (
    DataVersionManager, register_migration, get_migration_function,
    get_migration_path, compare_versions, CURRENT_VERSIONS
)

# Setup logger
logger = logging.getLogger(__name__)

# Migration context class
class MigrationContext:
    """Context for a data migration operation"""
    
    def __init__(self, 
                 db, 
                 collection_name: str,
                 from_version: str,
                 to_version: str,
                 dry_run: bool = False):
        """Initialize migration context
        
        Args:
            db: Database instance
            collection_name: Name of collection being migrated
            from_version: Starting version
            to_version: Target version
            dry_run: Whether to simulate the migration without making changes
        """
        self.db = db
        self.collection_name = collection_name
        self.from_version = from_version
        self.to_version = to_version
        self.dry_run = dry_run
        self.stats = {
            "documents_processed": 0,
            "documents_updated": 0,
            "documents_skipped": 0,
            "errors": 0,
            "start_time": datetime.utcnow(),
            "end_time": None,
            "duration_seconds": 0
        }
        self.errors = []
        self._collection = getattr(db, collection_name, None)
    
    def log(self, message: str, level: str = "info") -> None:
        """Log a message with the appropriate level
        
        Args:
            message: Message to log
            level: Log level (info, warning, error)
        """
        if level == "error":
            logger.error(f"Migration {self.collection_name} {self.from_version}->{self.to_version}: {message}")
        elif level == "warning":
            logger.warning(f"Migration {self.collection_name} {self.from_version}->{self.to_version}: {message}")
        else:
            logger.info(f"Migration {self.collection_name} {self.from_version}->{self.to_version}: {message}")
    
    async def update_document(self, document_id: Any, updates: Dict[str, Any]) -> bool:
        """Update a document in the collection
        
        Args:
            document_id: Document ID
            updates: Dictionary of updates to apply
            
        Returns:
            True if successful
        """
        if self.dry_run:
            self.log(f"Would update document {document_id} with {len(updates)} fields")
            return True
        
        if not self._collection:
            self.log(f"Collection {self.collection_name} not found", "error")
            self.errors.append(f"Collection {self.collection_name} not found")
            self.stats["errors"] += 1
            return False
        
        try:
            result = await self._collection.update_one(
                {"_id": document_id},
                {"$set": updates}
            )
            
            if result.modified_count > 0:
                self.stats["documents_updated"] += 1
                return True
            else:
                self.log(f"Document {document_id} not modified", "warning")
                self.stats["documents_skipped"] += 1
                return False
        except Exception as e:
            self.log(f"Error updating document {document_id}: {e}", "error")
            self.errors.append(f"Error updating document {document_id}: {e}")
            self.stats["errors"] += 1
            return False
    
    async def get_document(self, document_id: Any) -> Optional[Dict[str, Any]]:
        """Get a document from the collection
        
        Args:
            document_id: Document ID
            
        Returns:
            Document or None if not found
        """
        if not self._collection:
            self.log(f"Collection {self.collection_name} not found", "error")
            return None
        
        try:
            return await self._collection.find_one({"_id": document_id})
        except Exception as e:
            self.log(f"Error getting document {document_id}: {e}", "error")
            return None
    
    async def get_all_documents(self, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get all documents matching a query
        
        Args:
            query: Query filter
            
        Returns:
            List of documents
        """
        if not self._collection:
            self.log(f"Collection {self.collection_name} not found", "error")
            return []
        
        try:
            cursor = self._collection.find(query or {})
            return await cursor.to_list(length=None)
        except Exception as e:
            self.log(f"Error getting documents: {e}", "error")
            return []
    
    def complete(self) -> None:
        """Mark the migration as complete"""
        self.stats["end_time"] = datetime.utcnow()
        self.stats["duration_seconds"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        
        # Log summary
        self.log(f"Migration completed in {self.stats['duration_seconds']:.2f} seconds")
        self.log(f"Processed {self.stats['documents_processed']} documents")
        self.log(f"Updated {self.stats['documents_updated']} documents")
        self.log(f"Skipped {self.stats['documents_skipped']} documents")
        self.log(f"Encountered {self.stats['errors']} errors")

# Migration manager
class DataMigrationManager:
    """Manager for data migrations"""
    
    def __init__(self, db):
        """Initialize data migration manager
        
        Args:
            db: Database instance
        """
        self.db = db
        self.version_manager = None
    
    async def initialize(self) -> None:
        """Initialize the migration manager"""
        from utils.data_version import initialize_version_manager
        self.version_manager = await initialize_version_manager(self.db)
        
        # Register built-in migrations
        self._register_builtin_migrations()
    
    def _register_builtin_migrations(self) -> None:
        """Register built-in migrations for standard collections"""
        # Guild config migrations
        register_migration("guild_config", "1.0.0", self._migrate_guild_config_1_0_0)
        
        # User profiles migrations
        register_migration("user_profiles", "1.0.0", self._migrate_user_profiles_1_0_0)
        
        # Canvas data migrations
        register_migration("canvas_data", "1.0.0", self._migrate_canvas_data_1_0_0)
    
    async def _migrate_guild_config_1_0_0(self, context: MigrationContext) -> bool:
        """Migrate guild_config to version 1.0.0
        
        Args:
            context: Migration context
            
        Returns:
            True if successful
        """
        # Get all guild configs
        guild_configs = await context.get_all_documents()
        context.stats["documents_processed"] = len(guild_configs)
        
        for config in guild_configs:
            guild_id = config.get("guild_id")
            if not guild_id:
                context.log(f"Guild config missing guild_id: {config.get('_id')}", "warning")
                context.stats["documents_skipped"] += 1
                continue
            
            updates = {}
            
            # Ensure settings structure exists
            if "settings" not in config:
                updates["settings"] = {}
            
            # Migrate old settings format if needed
            for old_key in ["prefix", "language", "timezone", "premium"]:
                if old_key in config and old_key not in config.get("settings", {}):
                    if "settings" not in updates:
                        updates["settings"] = copy.deepcopy(config.get("settings", {}))
                    updates["settings"][old_key] = config[old_key]
            
            # Ensure integrations structure exists
            if "integrations" not in config:
                updates["integrations"] = {}
            
            # Apply updates if needed
            if updates:
                await context.update_document(config["_id"], updates)
        
        return True
    
    async def _migrate_user_profiles_1_0_0(self, context: MigrationContext) -> bool:
        """Migrate user_profiles to version 1.0.0
        
        Args:
            context: Migration context
            
        Returns:
            True if successful
        """
        # Get all user profiles
        user_profiles = await context.get_all_documents()
        context.stats["documents_processed"] = len(user_profiles)
        
        for profile in user_profiles:
            user_id = profile.get("user_id")
            if not user_id:
                context.log(f"User profile missing user_id: {profile.get('_id')}", "warning")
                context.stats["documents_skipped"] += 1
                continue
            
            updates = {}
            
            # Ensure inventory exists
            if "inventory" not in profile:
                updates["inventory"] = {
                    "credits": 0,
                    "colors": [],
                    "items": []
                }
            
            # Ensure stats exists
            if "stats" not in profile:
                updates["stats"] = {
                    "commands_used": 0,
                    "canvas_pixels_placed": 0,
                    "daily_streak": 0
                }
            
            # Update old balance to credits if needed
            if "balance" in profile and "inventory" in profile and "credits" not in profile["inventory"]:
                if "inventory" not in updates:
                    updates["inventory"] = copy.deepcopy(profile.get("inventory", {}))
                updates["inventory"]["credits"] = profile["balance"]
            
            # Apply updates if needed
            if updates:
                await context.update_document(profile["_id"], updates)
        
        return True
    
    async def _migrate_canvas_data_1_0_0(self, context: MigrationContext) -> bool:
        """Migrate canvas_data to version 1.0.0
        
        Args:
            context: Migration context
            
        Returns:
            True if successful
        """
        # Get all canvas data
        canvas_documents = await context.get_all_documents()
        context.stats["documents_processed"] = len(canvas_documents)
        
        for canvas in canvas_documents:
            guild_id = canvas.get("guild_id")
            if not guild_id:
                context.log(f"Canvas data missing guild_id: {canvas.get('_id')}", "warning")
                context.stats["documents_skipped"] += 1
                continue
            
            updates = {}
            
            # Ensure stats structure exists
            if "stats" not in canvas:
                updates["stats"] = {
                    "total_pixels_placed": 0,
                    "unique_users": 0,
                    "last_update": datetime.utcnow()
                }
            
            # Count pixels if needed
            if "pixels" in canvas and "stats" in canvas and "total_pixels_placed" not in canvas["stats"]:
                if "stats" not in updates:
                    updates["stats"] = copy.deepcopy(canvas.get("stats", {}))
                updates["stats"]["total_pixels_placed"] = len(canvas["pixels"])
                
                # Count unique users
                unique_users = set()
                for pixel_data in canvas["pixels"].values():
                    if isinstance(pixel_data, dict) and "user_id" in pixel_data:
                        unique_users.add(pixel_data["user_id"])
                updates["stats"]["unique_users"] = len(unique_users)
            
            # Apply updates if needed
            if updates:
                await context.update_document(canvas["_id"], updates)
        
        return True
    
    async def analyze_migration_needs(self) -> Dict[str, Dict[str, Any]]:
        """Analyze which collections need migration
        
        Returns:
            Dictionary with migration analysis
        """
        if not self.version_manager:
            await self.initialize()
        
        return await self.version_manager.analyze_migration_needs()
    
    async def migrate_collection(self, 
                               collection: str, 
                               to_version: Optional[str] = None,
                               dry_run: bool = False) -> Dict[str, Any]:
        """Migrate a collection to a target version
        
        Args:
            collection: Collection name
            to_version: Target version (default: current version)
            dry_run: Whether to simulate the migration without making changes
            
        Returns:
            Dictionary with migration results
        """
        if not self.version_manager:
            await self.initialize()
        
        if to_version is None:
            to_version = CURRENT_VERSIONS.get(collection)
            if not to_version:
                return {
                    "success": False,
                    "error": f"No current version defined for collection {collection}"
                }
        
        # Get current version
        current_version = await self.version_manager.get_collection_version(collection)
        
        # Check if migration is needed
        if compare_versions(current_version, to_version) >= 0:
            return {
                "success": True,
                "message": f"Collection {collection} is already at version {current_version}",
                "version": current_version,
                "migrated": False
            }
        
        # Get migration path
        migration_path = get_migration_path(current_version, to_version, collection)
        if not migration_path:
            return {
                "success": False,
                "error": f"No migration path found from {current_version} to {to_version} for {collection}"
            }
        
        # Execute migrations
        results = []
        current = current_version
        
        for target in migration_path:
            migration_func = get_migration_function(collection, target)
            if not migration_func:
                return {
                    "success": False,
                    "error": f"Migration function not found for {collection} to {target}",
                    "partial_results": results
                }
            
            # Create migration context
            context = MigrationContext(
                db=self.db,
                collection_name=collection,
                from_version=current,
                to_version=target,
                dry_run=dry_run
            )
            
            # Execute migration
            try:
                logger.info(f"Migrating {collection} from {current} to {target}")
                success = await migration_func(context)
                context.complete()
                
                if not success:
                    return {
                        "success": False,
                        "error": f"Migration from {current} to {target} failed",
                        "context": context.stats,
                        "errors": context.errors,
                        "partial_results": results
                    }
                
                # Update version if not dry run
                if not dry_run:
                    await self.version_manager.set_collection_version(collection, target)
                
                results.append({
                    "from": current,
                    "to": target,
                    "stats": context.stats,
                    "errors": context.errors
                })
                
                current = target
            except Exception as e:
                logger.error(f"Error during migration {collection} {current}->{target}: {e}")
                return {
                    "success": False,
                    "error": f"Migration error: {type(e).__name__}: {e}",
                    "partial_results": results
                }
        
        return {
            "success": True,
            "message": f"Successfully migrated {collection} from {current_version} to {to_version}",
            "version": to_version,
            "migrated": True,
            "steps": results
        }
    
    async def migrate_all_collections(self, dry_run: bool = False) -> Dict[str, Dict[str, Any]]:
        """Migrate all collections to their current versions
        
        Args:
            dry_run: Whether to simulate the migration without making changes
            
        Returns:
            Dictionary mapping collection names to migration results
        """
        if not self.version_manager:
            await self.initialize()
        
        # Get migration needs
        needs = await self.analyze_migration_needs()
        
        # Execute migrations
        results = {}
        
        for collection, info in needs.items():
            if info["needs_migration"] and info["can_migrate"]:
                results[collection] = await self.migrate_collection(
                    collection=collection,
                    to_version=info["target_version"],
                    dry_run=dry_run
                )
            else:
                results[collection] = {
                    "success": True,
                    "message": f"Collection {collection} is up to date",
                    "version": info["current_version"],
                    "migrated": False
                }
        
        return results
    
    async def generate_migration_report(self) -> str:
        """Generate a report of migration status
        
        Returns:
            Markdown formatted report
        """
        if not self.version_manager:
            await self.initialize()
        
        # Get current versions
        current_versions = await self.version_manager.get_all_versions()
        
        # Get migration needs
        needs = await self.analyze_migration_needs()
        
        # Build report
        report = "# Data Migration Status Report\n\n"
        report += f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += "## Collection Versions\n\n"
        report += "| Collection | Current | Target | Status |\n"
        report += "|------------|---------|--------|--------|\n"
        
        for collection, target in CURRENT_VERSIONS.items():
            current = current_versions.get(collection, "0.0.0")
            
            if compare_versions(current, target) < 0:
                status = "⚠️ Needs Migration"
            else:
                status = "✅ Up to Date"
            
            report += f"| {collection} | {current} | {target} | {status} |\n"
        
        report += "\n## Migration Analysis\n\n"
        
        needs_migration = False
        for collection, info in needs.items():
            if info["needs_migration"]:
                if not needs_migration:
                    report += "Collections requiring migration:\n\n"
                    needs_migration = True
                
                report += f"### {collection}\n\n"
                report += f"- Current version: {info['current_version']}\n"
                report += f"- Target version: {info['target_version']}\n"
                
                if info["can_migrate"]:
                    report += f"- Migration path: {' -> '.join([info['current_version']] + info['migration_path'])}\n"
                    report += "- Status: Ready to migrate\n"
                else:
                    report += "- Status: ⚠️ No migration path available\n"
                
                report += "\n"
        
        if not needs_migration:
            report += "All collections are up to date! 🎉\n"
        
        return report

# Create a global instance for convenience
_migration_manager = None

async def get_migration_manager(db) -> DataMigrationManager:
    """Get the global migration manager instance
    
    Args:
        db: Database instance
        
    Returns:
        DataMigrationManager instance
    """
    global _migration_manager
    
    if _migration_manager is None:
        _migration_manager = DataMigrationManager(db)
        await _migration_manager.initialize()
    
    return _migration_manager