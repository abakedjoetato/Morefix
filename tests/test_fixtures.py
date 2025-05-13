"""
Test Fixtures for Tower of Temptation PvP Statistics Bot

This module provides database fixtures for testing:
1. Guild configuration fixtures
2. User profile fixtures 
3. Stats record fixtures
4. Error record fixtures
5. Mock MongoDB setup

These fixtures allow for consistent testing environments
without requiring an actual database connection.
"""
import asyncio
import datetime
import uuid
import os
import json
import random
from typing import Dict, List, Any, Optional, Union
from unittest.mock import MagicMock, AsyncMock

# Mock MongoDB collections and database
class MockCollection:
    """Mock MongoDB collection"""
    
    def __init__(self, name, initial_data=None):
        """Initialize a mock collection
        
        Args:
            name: Collection name
            initial_data: Initial data for the collection (list of documents)
        """
        self.name = name
        self._data = []
        
        # Add initial data if provided
        if initial_data:
            for doc in initial_data:
                # Ensure all documents have an _id
                if '_id' not in doc:
                    doc['_id'] = str(uuid.uuid4())
                self._data.append(doc)
        
        # Create async methods
        self.find = AsyncMock(side_effect=self._find)
        self.find_one = AsyncMock(side_effect=self._find_one)
        self.insert_one = AsyncMock(side_effect=self._insert_one)
        self.insert_many = AsyncMock(side_effect=self._insert_many)
        self.update_one = AsyncMock(side_effect=self._update_one)
        self.update_many = AsyncMock(side_effect=self._update_many)
        self.delete_one = AsyncMock(side_effect=self._delete_one)
        self.delete_many = AsyncMock(side_effect=self._delete_many)
        self.count_documents = AsyncMock(side_effect=self._count_documents)
        self.aggregate = AsyncMock(side_effect=self._aggregate)
    
    async def _find(self, query=None, projection=None, sort=None, limit=None, skip=None):
        """Mock find operation
        
        Args:
            query: Query filter
            projection: Field projection
            sort: Sort specification
            limit: Result limit
            skip: Number of docs to skip
            
        Returns:
            MockCursor with matching documents
        """
        results = []
        
        # Apply query filter
        if query:
            for doc in self._data:
                if self._matches_query(doc, query):
                    results.append(doc.copy())
        else:
            results = [doc.copy() for doc in self._data]
        
        # Apply projection
        if projection:
            results = self._apply_projection(results, projection)
        
        # Apply sort
        if sort:
            results = self._apply_sort(results, sort)
        
        # Apply skip
        if skip:
            results = results[skip:]
        
        # Apply limit
        if limit:
            results = results[:limit]
        
        return MockCursor(results)
    
    async def _find_one(self, query=None, projection=None):
        """Mock find_one operation
        
        Args:
            query: Query filter
            projection: Field projection
            
        Returns:
            Matching document or None
        """
        # Apply query filter
        if query:
            for doc in self._data:
                if self._matches_query(doc, query):
                    result = doc.copy()
                    
                    # Apply projection
                    if projection:
                        result = self._apply_projection([result], projection)[0]
                    
                    return result
            return None
        elif self._data:
            result = self._data[0].copy()
            
            # Apply projection
            if projection:
                result = self._apply_projection([result], projection)[0]
            
            return result
        else:
            return None
    
    async def _insert_one(self, document):
        """Mock insert_one operation
        
        Args:
            document: Document to insert
            
        Returns:
            Mock insert result
        """
        # Ensure document has an _id
        if '_id' not in document:
            document['_id'] = str(uuid.uuid4())
        
        # Insert a copy of the document
        self._data.append(document.copy())
        
        # Return mock insert result
        result = MagicMock()
        result.inserted_id = document['_id']
        return result
    
    async def _insert_many(self, documents):
        """Mock insert_many operation
        
        Args:
            documents: Documents to insert
            
        Returns:
            Mock insert result
        """
        inserted_ids = []
        
        for doc in documents:
            # Ensure document has an _id
            if '_id' not in doc:
                doc['_id'] = str(uuid.uuid4())
            
            # Insert a copy of the document
            self._data.append(doc.copy())
            inserted_ids.append(doc['_id'])
        
        # Return mock insert result
        result = MagicMock()
        result.inserted_ids = inserted_ids
        return result
    
    async def _update_one(self, query, update, upsert=False):
        """Mock update_one operation
        
        Args:
            query: Query filter
            update: Update specification
            upsert: Whether to insert if no match
            
        Returns:
            Mock update result
        """
        # Try to find a matching document
        for i, doc in enumerate(self._data):
            if self._matches_query(doc, query):
                # Update the document
                self._data[i] = self._apply_update(doc, update)
                
                # Return mock update result
                result = MagicMock()
                result.matched_count = 1
                result.modified_count = 1
                result.upserted_id = None
                return result
        
        # No match found, handle upsert
        if upsert:
            # Create new document from query and update
            new_doc = {}
            
            # Add query fields
            for k, v in query.items():
                if isinstance(v, dict):
                    continue  # Skip operators like $eq
                new_doc[k] = v
            
            # Apply update
            new_doc = self._apply_update(new_doc, update)
            
            # Ensure document has an _id
            if '_id' not in new_doc:
                new_doc['_id'] = str(uuid.uuid4())
            
            # Insert the document
            self._data.append(new_doc)
            
            # Return mock update result
            result = MagicMock()
            result.matched_count = 0
            result.modified_count = 0
            result.upserted_id = new_doc['_id']
            return result
        
        # Return empty result
        result = MagicMock()
        result.matched_count = 0
        result.modified_count = 0
        result.upserted_id = None
        return result
    
    async def _update_many(self, query, update, upsert=False):
        """Mock update_many operation
        
        Args:
            query: Query filter
            update: Update specification
            upsert: Whether to insert if no match
            
        Returns:
            Mock update result
        """
        matched_count = 0
        modified_count = 0
        
        # Find all matching documents
        for i, doc in enumerate(self._data):
            if self._matches_query(doc, query):
                # Update the document
                self._data[i] = self._apply_update(doc, update)
                matched_count += 1
                modified_count += 1
        
        # No match found, handle upsert
        if matched_count == 0 and upsert:
            # Create new document from query and update
            new_doc = {}
            
            # Add query fields
            for k, v in query.items():
                if isinstance(v, dict):
                    continue  # Skip operators like $eq
                new_doc[k] = v
            
            # Apply update
            new_doc = self._apply_update(new_doc, update)
            
            # Ensure document has an _id
            if '_id' not in new_doc:
                new_doc['_id'] = str(uuid.uuid4())
            
            # Insert the document
            self._data.append(new_doc)
            
            # Return mock update result
            result = MagicMock()
            result.matched_count = 0
            result.modified_count = 0
            result.upserted_id = new_doc['_id']
            return result
        
        # Return result
        result = MagicMock()
        result.matched_count = matched_count
        result.modified_count = modified_count
        result.upserted_id = None
        return result
    
    async def _delete_one(self, query):
        """Mock delete_one operation
        
        Args:
            query: Query filter
            
        Returns:
            Mock delete result
        """
        # Try to find a matching document
        for i, doc in enumerate(self._data):
            if self._matches_query(doc, query):
                # Delete the document
                del self._data[i]
                
                # Return mock delete result
                result = MagicMock()
                result.deleted_count = 1
                return result
        
        # Return empty result
        result = MagicMock()
        result.deleted_count = 0
        return result
    
    async def _delete_many(self, query):
        """Mock delete_many operation
        
        Args:
            query: Query filter
            
        Returns:
            Mock delete result
        """
        # Find all matching documents
        to_delete = []
        for i, doc in enumerate(self._data):
            if self._matches_query(doc, query):
                to_delete.append(i)
        
        # Delete documents in reverse order to avoid index issues
        to_delete.sort(reverse=True)
        for i in to_delete:
            del self._data[i]
        
        # Return result
        result = MagicMock()
        result.deleted_count = len(to_delete)
        return result
    
    async def _count_documents(self, query=None):
        """Mock count_documents operation
        
        Args:
            query: Query filter
            
        Returns:
            Count of matching documents
        """
        count = 0
        
        # Apply query filter
        if query:
            for doc in self._data:
                if self._matches_query(doc, query):
                    count += 1
        else:
            count = len(self._data)
        
        return count
    
    async def _aggregate(self, pipeline):
        """Mock aggregate operation
        
        Args:
            pipeline: Aggregation pipeline
            
        Returns:
            MockCursor with aggregation results
        """
        # Simple implementation supports only a subset of MongoDB aggregation
        results = [doc.copy() for doc in self._data]
        
        for stage in pipeline:
            # Match stage
            if '$match' in stage:
                results = [doc for doc in results if self._matches_query(doc, stage['$match'])]
            
            # Group stage
            elif '$group' in stage:
                group_spec = stage['$group']
                
                # Get group key
                id_spec = group_spec['_id']
                grouped = {}
                
                for doc in results:
                    # Compute group key
                    group_key = self._compute_group_key(doc, id_spec)
                    
                    # Initialize group if needed
                    if group_key not in grouped:
                        grouped[group_key] = {'_id': group_key}
                    
                    # Update accumulators
                    for field, accumulator in group_spec.items():
                        if field == '_id':
                            continue
                        
                        # Sum
                        if '$sum' in accumulator:
                            value = 1  # Simple case: count
                            if accumulator['$sum'] != 1:
                                value = self._extract_field(doc, accumulator['$sum'])
                            
                            if field not in grouped[group_key]:
                                grouped[group_key][field] = 0
                            grouped[group_key][field] += value
                        
                        # Average
                        elif '$avg' in accumulator:
                            value = self._extract_field(doc, accumulator['$avg'])
                            
                            if field not in grouped[group_key]:
                                grouped[group_key][field + '_sum'] = 0
                                grouped[group_key][field + '_count'] = 0
                            
                            grouped[group_key][field + '_sum'] += value
                            grouped[group_key][field + '_count'] += 1
                            grouped[group_key][field] = grouped[group_key][field + '_sum'] / grouped[group_key][field + '_count']
                        
                        # Max
                        elif '$max' in accumulator:
                            value = self._extract_field(doc, accumulator['$max'])
                            
                            if field not in grouped[group_key] or value > grouped[group_key][field]:
                                grouped[group_key][field] = value
                        
                        # Min
                        elif '$min' in accumulator:
                            value = self._extract_field(doc, accumulator['$min'])
                            
                            if field not in grouped[group_key] or value < grouped[group_key][field]:
                                grouped[group_key][field] = value
                
                # Convert grouped results back to list
                results = list(grouped.values())
            
            # Project stage
            elif '$project' in stage:
                project_spec = stage['$project']
                results = self._apply_projection(results, project_spec)
            
            # Sort stage
            elif '$sort' in stage:
                sort_spec = stage['$sort']
                results = self._apply_sort(results, sort_spec)
            
            # Limit stage
            elif '$limit' in stage:
                limit = stage['$limit']
                results = results[:limit]
            
            # Skip stage
            elif '$skip' in stage:
                skip = stage['$skip']
                results = results[skip:]
        
        return MockCursor(results)
    
    def _matches_query(self, doc, query):
        """Check if a document matches a query
        
        Args:
            doc: Document to check
            query: Query to match against
            
        Returns:
            True if document matches, False otherwise
        """
        for key, value in query.items():
            # Handle operators
            if key.startswith('$'):
                if key == '$and':
                    for sub_query in value:
                        if not self._matches_query(doc, sub_query):
                            return False
                    return True
                
                elif key == '$or':
                    for sub_query in value:
                        if self._matches_query(doc, sub_query):
                            return True
                    return False
                
                # Add other operators as needed
                
                return False
            
            # Handle field not in document
            if key not in doc:
                return False
            
            # Handle nested query
            if isinstance(value, dict) and any(k.startswith('$') for k in value.keys()):
                field_value = doc[key]
                
                for op, op_value in value.items():
                    if op == '$eq':
                        if field_value != op_value:
                            return False
                    
                    elif op == '$ne':
                        if field_value == op_value:
                            return False
                    
                    elif op == '$gt':
                        if not field_value > op_value:
                            return False
                    
                    elif op == '$gte':
                        if not field_value >= op_value:
                            return False
                    
                    elif op == '$lt':
                        if not field_value < op_value:
                            return False
                    
                    elif op == '$lte':
                        if not field_value <= op_value:
                            return False
                    
                    elif op == '$in':
                        if field_value not in op_value:
                            return False
                    
                    elif op == '$nin':
                        if field_value in op_value:
                            return False
                    
                    # Add other operators as needed
            
            # Direct value comparison
            elif doc[key] != value:
                return False
        
        return True
    
    def _apply_update(self, doc, update):
        """Apply an update to a document
        
        Args:
            doc: Document to update
            update: Update specification
            
        Returns:
            Updated document
        """
        result = doc.copy()
        
        for operator, fields in update.items():
            if operator == '$set':
                for field, value in fields.items():
                    # Handle nested fields
                    parts = field.split('.')
                    if len(parts) > 1:
                        target = result
                        for part in parts[:-1]:
                            if part not in target:
                                target[part] = {}
                            target = target[part]
                        target[parts[-1]] = value
                    else:
                        result[field] = value
            
            elif operator == '$inc':
                for field, value in fields.items():
                    # Handle nested fields
                    parts = field.split('.')
                    if len(parts) > 1:
                        target = result
                        for part in parts[:-1]:
                            if part not in target:
                                target[part] = {}
                            target = target[part]
                        if parts[-1] not in target:
                            target[parts[-1]] = 0
                        target[parts[-1]] += value
                    else:
                        if field not in result:
                            result[field] = 0
                        result[field] += value
            
            elif operator == '$push':
                for field, value in fields.items():
                    # Handle nested fields
                    parts = field.split('.')
                    if len(parts) > 1:
                        target = result
                        for part in parts[:-1]:
                            if part not in target:
                                target[part] = {}
                            target = target[part]
                        if parts[-1] not in target:
                            target[parts[-1]] = []
                        target[parts[-1]].append(value)
                    else:
                        if field not in result:
                            result[field] = []
                        result[field].append(value)
            
            elif operator == '$pull':
                for field, value in fields.items():
                    # Handle nested fields
                    parts = field.split('.')
                    if len(parts) > 1:
                        target = result
                        for part in parts[:-1]:
                            if part not in target:
                                continue
                            target = target[part]
                        if parts[-1] not in target:
                            continue
                        if isinstance(target[parts[-1]], list):
                            target[parts[-1]] = [v for v in target[parts[-1]] if v != value]
                    else:
                        if field in result and isinstance(result[field], list):
                            result[field] = [v for v in result[field] if v != value]
            
            # Add other operators as needed
        
        return result
    
    def _apply_projection(self, documents, projection):
        """Apply a projection to documents
        
        Args:
            documents: Documents to project
            projection: Projection specification
            
        Returns:
            Projected documents
        """
        results = []
        include_mode = True
        
        # Determine projection mode (include or exclude)
        for k, v in projection.items():
            if k != '_id':
                include_mode = bool(v)
                break
        
        for doc in documents:
            result = {}
            
            if include_mode:
                # Include specified fields and maybe _id
                for field, include in projection.items():
                    if include:
                        if field in doc:
                            result[field] = doc[field]
                
                # Special handling for _id
                if '_id' in projection:
                    if projection['_id']:
                        result['_id'] = doc['_id']
                else:
                    result['_id'] = doc['_id']
            else:
                # Include all fields except those specified
                result = doc.copy()
                for field, exclude in projection.items():
                    if exclude and field in result:
                        del result[field]
            
            results.append(result)
        
        return results
    
    def _apply_sort(self, documents, sort_spec):
        """Apply a sort to documents
        
        Args:
            documents: Documents to sort
            sort_spec: Sort specification
            
        Returns:
            Sorted documents
        """
        def sort_key(doc):
            """Create a key for sorting based on sort specification"""
            key = []
            for field, direction in sort_spec.items():
                # Handle nested fields
                parts = field.split('.')
                value = doc
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                
                # Add to key with appropriate direction
                if direction >= 0:
                    key.append(value)
                else:
                    # Reverse sort for negative direction
                    # Use tuple to handle None values properly
                    if value is None:
                        key.append((1, None))
                    else:
                        key.append((0, value))
            
            return tuple(key)
        
        return sorted(documents, key=sort_key)
    
    def _compute_group_key(self, doc, id_spec):
        """Compute a group key based on an _id specification
        
        Args:
            doc: Document to get key from
            id_spec: _id specification from $group
            
        Returns:
            Group key (as a string or tuple)
        """
        if isinstance(id_spec, str) and id_spec.startswith('$'):
            # Simple field reference
            field = id_spec[1:]
            return self._extract_field(doc, field)
        
        elif isinstance(id_spec, dict):
            # Compound key
            key = {}
            for k, v in id_spec.items():
                if isinstance(v, str) and v.startswith('$'):
                    field = v[1:]
                    key[k] = self._extract_field(doc, field)
                else:
                    key[k] = v
            
            # Convert to tuple for hashability
            return tuple(sorted(key.items()))
        
        # Literal value
        return id_spec
    
    def _extract_field(self, doc, field_path):
        """Extract a field value from a document
        
        Args:
            doc: Document to extract from
            field_path: Field path (can be nested)
            
        Returns:
            Field value or None
        """
        if isinstance(field_path, str) and field_path.startswith('$'):
            field_path = field_path[1:]
        
        # Handle nested fields
        parts = field_path.split('.')
        value = doc
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value

class MockCursor:
    """Mock MongoDB cursor"""
    
    def __init__(self, documents):
        """Initialize a mock cursor
        
        Args:
            documents: List of documents
        """
        self._documents = documents
        self._index = 0
    
    def __aiter__(self):
        """Async iterator
        
        Returns:
            Self
        """
        self._index = 0
        return self
    
    async def __anext__(self):
        """Get next document
        
        Returns:
            Next document
            
        Raises:
            StopAsyncIteration when no more documents
        """
        if self._index < len(self._documents):
            doc = self._documents[self._index]
            self._index += 1
            return doc
        raise StopAsyncIteration
    
    async def to_list(self, length=None):
        """Convert cursor to list
        
        Args:
            length: Maximum number of documents
            
        Returns:
            List of documents
        """
        if length is None:
            return self._documents
        return self._documents[:length]

class MockDatabase:
    """Mock MongoDB database"""
    
    def __init__(self, name, collections=None):
        """Initialize a mock database
        
        Args:
            name: Database name
            collections: Dictionary of collection name to initial data
        """
        self.name = name
        self._collections = {}
        
        # Initialize collections
        if collections:
            for name, data in collections.items():
                self._collections[name] = MockCollection(name, data)
    
    def __getattr__(self, name):
        """Get a collection by name
        
        Args:
            name: Collection name
            
        Returns:
            MockCollection instance
        """
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]
    
    def get_collection(self, name):
        """Get a collection by name
        
        Args:
            name: Collection name
            
        Returns:
            MockCollection instance
        """
        return self.__getattr__(name)

class MockMongoClient:
    """Mock MongoDB client"""
    
    def __init__(self, uri=None, databases=None):
        """Initialize a mock client
        
        Args:
            uri: Connection URI (ignored)
            databases: Dictionary of database name to MockDatabase
        """
        self._databases = {}
        
        # Initialize databases
        if databases:
            self._databases.update(databases)
    
    def __getattr__(self, name):
        """Get a database by name
        
        Args:
            name: Database name
            
        Returns:
            MockDatabase instance
        """
        if name not in self._databases:
            self._databases[name] = MockDatabase(name)
        return self._databases[name]
    
    def get_database(self, name):
        """Get a database by name
        
        Args:
            name: Database name
            
        Returns:
            MockDatabase instance
        """
        return self.__getattr__(name)
    
    async def server_info(self):
        """Get server info
        
        Returns:
            Mock server info
        """
        return {
            "version": "4.4.0",
            "ok": 1.0
        }

# Guild configuration fixtures
def create_guild_config_fixtures(num_guilds=3):
    """Create guild configuration fixtures
    
    Args:
        num_guilds: Number of guilds to create
        
    Returns:
        List of guild config documents
    """
    fixtures = []
    
    for i in range(1, num_guilds + 1):
        guild_id = f"1{i:08d}"
        
        fixture = {
            "_id": f"guild:{guild_id}",
            "guild_id": guild_id,
            "name": f"Test Guild {i}",
            "prefix": "!" if i % 2 == 0 else "/",
            "settings": {
                "canvas_enabled": i % 3 != 0,
                "canvas_size": 32 if i % 2 == 0 else 64,
                "canvas_default_color": "#FFFFFF",
                "canvas_update_interval": 60,
                "premium": i % 4 == 0,
                "daily_limit": 100,
                "rate_limit": 10 if i % 2 == 0 else 20,
                "timezone": "UTC" if i % 2 == 0 else "America/New_York",
                "language": "en" if i % 3 == 0 else ("fr" if i % 3 == 1 else "es"),
                "log_channel": f"1{i}0000001" if i % 2 == 0 else None,
                "admin_role": f"1{i}0000002" if i % 2 == 0 else None
            },
            "integrations": {
                "sftp": {
                    "enabled": i % 3 == 0,
                    "host": f"sftp.example{i}.com",
                    "port": 22,
                    "username": f"user{i}",
                    "password": f"password{i}",
                    "base_path": f"/home/user{i}/logs",
                    "auto_sync": i % 2 == 0,
                    "last_sync": datetime.datetime.now() - datetime.timedelta(hours=i)
                },
                "webhooks": {
                    "enabled": i % 4 == 0,
                    "url": f"https://discord.com/api/webhooks/1{i}00000000/example{i}"
                }
            },
            "stats": {
                "commands_used": i * 10,
                "canvas_pixels_placed": i * 100,
                "errors_encountered": i,
                "users_active": i * 5,
                "last_activity": datetime.datetime.now() - datetime.timedelta(minutes=i * 10)
            },
            "created_at": datetime.datetime.now() - datetime.timedelta(days=i * 10),
            "updated_at": datetime.datetime.now() - datetime.timedelta(hours=i)
        }
        
        fixtures.append(fixture)
    
    return fixtures

# User profile fixtures
def create_user_profile_fixtures(num_users=5, guild_ids=None):
    """Create user profile fixtures
    
    Args:
        num_users: Number of users to create
        guild_ids: List of guild IDs to associate users with
        
    Returns:
        List of user profile documents
    """
    if guild_ids is None:
        guild_ids = [f"1{i:08d}" for i in range(1, 4)]
    
    fixtures = []
    
    for i in range(1, num_users + 1):
        user_id = f"2{i:08d}"
        
        # Assign to random guilds
        user_guilds = random.sample(guild_ids, min(len(guild_ids), random.randint(1, len(guild_ids))))
        
        fixture = {
            "_id": f"user:{user_id}",
            "user_id": user_id,
            "username": f"TestUser{i}",
            "discriminator": f"{i:04d}",
            "guilds": user_guilds,
            "settings": {
                "theme": "dark" if i % 2 == 0 else "light",
                "notifications": i % 3 != 0,
                "default_color": f"#{i:06x}",
                "timezone": "UTC" if i % 2 == 0 else "America/Los_Angeles"
            },
            "stats": {
                "commands_used": i * 5,
                "canvas_pixels_placed": i * 50,
                "daily_streak": i % 7,
                "rank": num_users - i + 1,
                "last_active": datetime.datetime.now() - datetime.timedelta(hours=i)
            },
            "inventory": {
                "credits": i * 100,
                "premium_until": datetime.datetime.now() + datetime.timedelta(days=i * 30) if i % 3 == 0 else None,
                "items": [
                    {"id": f"item{j}", "name": f"Test Item {j}", "quantity": j} 
                    for j in range(1, min(5, i + 1))
                ],
                "colors": [f"#{j:06x}" for j in range(1, min(5, i + 1))],
                "boosters": [
                    {"id": f"booster{j}", "name": f"Test Booster {j}", "multiplier": j, "expires_at": datetime.datetime.now() + datetime.timedelta(days=j)}
                    for j in range(1, min(3, i + 1)) if i % 2 == 0
                ]
            },
            "created_at": datetime.datetime.now() - datetime.timedelta(days=i * 15),
            "updated_at": datetime.datetime.now() - datetime.timedelta(hours=i * 2)
        }
        
        fixtures.append(fixture)
    
    return fixtures

# Stats record fixtures
def create_stats_record_fixtures(num_records=20, guild_ids=None, user_ids=None):
    """Create stats record fixtures
    
    Args:
        num_records: Number of records to create
        guild_ids: List of guild IDs
        user_ids: List of user IDs
        
    Returns:
        List of stats record documents
    """
    if guild_ids is None:
        guild_ids = [f"1{i:08d}" for i in range(1, 4)]
    
    if user_ids is None:
        user_ids = [f"2{i:08d}" for i in range(1, 6)]
    
    fixtures = []
    now = datetime.datetime.now()
    
    for i in range(1, num_records + 1):
        # Choose random guild and user
        guild_id = random.choice(guild_ids)
        user_id = random.choice(user_ids)
        
        # Create timestamp with decreasing time
        timestamp = now - datetime.timedelta(hours=i * 2)
        
        fixture = {
            "_id": f"stats:{i}",
            "guild_id": guild_id,
            "user_id": user_id,
            "timestamp": timestamp,
            "type": random.choice(["command", "canvas", "login", "purchase"]),
            "data": {
                "command": f"test_command_{i % 5}" if i % 4 == 0 else None,
                "pixels_placed": i % 10 if i % 3 == 0 else None,
                "credits_spent": i * 10 if i % 5 == 0 else None,
                "duration": i * 60 if i % 2 == 0 else None,
                "success": i % 7 != 0
            },
            "metadata": {
                "client": "desktop" if i % 2 == 0 else "mobile",
                "version": f"v1.{i % 10}",
                "region": random.choice(["us-east", "us-west", "eu-central", "asia"]),
                "latency": random.randint(50, 500)
            }
        }
        
        fixtures.append(fixture)
    
    return fixtures

# Error record fixtures
def create_error_record_fixtures(num_errors=15, guild_ids=None, user_ids=None):
    """Create error record fixtures
    
    Args:
        num_errors: Number of errors to create
        guild_ids: List of guild IDs
        user_ids: List of user IDs
        
    Returns:
        List of error record documents
    """
    if guild_ids is None:
        guild_ids = [f"1{i:08d}" for i in range(1, 4)]
    
    if user_ids is None:
        user_ids = [f"2{i:08d}" for i in range(1, 6)]
    
    error_types = [
        "CommandInvokeError",
        "MissingPermissions",
        "InvalidArgument",
        "TimeoutError",
        "DatabaseError",
        "SFTPError",
        "DiscordAPIError",
        "RateLimitError"
    ]
    
    error_categories = [
        "command",
        "permission",
        "validation",
        "timeout",
        "database",
        "sftp",
        "discord_api",
        "rate_limit"
    ]
    
    fixtures = []
    now = datetime.datetime.now()
    
    for i in range(1, num_errors + 1):
        # Choose random guild, user, and error type
        guild_id = random.choice(guild_ids)
        user_id = random.choice(user_ids) if i % 3 != 0 else None
        error_type = random.choice(error_types)
        category = random.choice(error_categories)
        
        # Generate fingerprint for grouping similar errors
        fingerprint = f"{error_type}:{i % 5}"
        
        # Create timestamp with decreasing time
        timestamp = now - datetime.timedelta(hours=i * 4)
        
        fixture = {
            "_id": f"error:{i}",
            "id": str(uuid.uuid4()),
            "timestamp": timestamp,
            "category": category,
            "error_type": error_type,
            "error_message": f"Test error message {i} of type {error_type}",
            "fingerprint": fingerprint,
            "traceback": f"Traceback (most recent call last):\n  File \"test.py\", line {i}, in test_function\n    raise {error_type}(\"Test error message {i}\")",
            "context": {
                "guild_id": guild_id,
                "user_id": user_id,
                "command": f"test_command_{i % 5}" if i % 2 == 0 else None,
                "channel_id": f"{guild_id[:5]}000{i}" if i % 3 == 0 else None
            },
            "normalized_message": f"Test error message of type {error_type}",
            "occurrence_count": i % 3 + 1,
            "first_seen": timestamp,
            "last_seen": timestamp,
            "is_resolved": i % 7 == 0,
            "resolution_notes": f"Fixed in v1.{i}" if i % 7 == 0 else None
        }
        
        fixtures.append(fixture)
    
    return fixtures

# Canvas data fixtures
def create_canvas_data_fixtures(num_canvases=2, guild_ids=None):
    """Create canvas data fixtures
    
    Args:
        num_canvases: Number of canvases to create
        guild_ids: List of guild IDs
        
    Returns:
        List of canvas data documents
    """
    if guild_ids is None:
        guild_ids = [f"1{i:08d}" for i in range(1, num_canvases + 1)]
    
    fixtures = []
    now = datetime.datetime.now()
    
    for i, guild_id in enumerate(guild_ids[:num_canvases]):
        # Create a simple checker pattern
        size = 32 if i % 2 == 0 else 64
        pixels = {}
        
        for x in range(size):
            for y in range(size):
                if (x + y) % 2 == 0:
                    continue  # Leave as default color
                
                # Create a color based on position
                r = (x * 255) // size
                g = (y * 255) // size
                b = ((x + y) * 255) // (size * 2)
                color = f"#{r:02x}{g:02x}{b:02x}"
                
                pixels[f"{x},{y}"] = {
                    "color": color,
                    "user_id": f"2{(x * size + y) % 5 + 1:08d}",
                    "timestamp": now - datetime.timedelta(minutes=(x * size + y))
                }
        
        fixture = {
            "_id": f"canvas:{guild_id}",
            "guild_id": guild_id,
            "size": size,
            "default_color": "#FFFFFF",
            "pixels": pixels,
            "stats": {
                "total_pixels_placed": len(pixels),
                "unique_users": 5,
                "last_update": now - datetime.timedelta(minutes=1)
            },
            "created_at": now - datetime.timedelta(days=i + 1),
            "updated_at": now - datetime.timedelta(minutes=1)
        }
        
        fixtures.append(fixture)
    
    return fixtures

# Create a complete test database
def create_test_database():
    """Create a complete test database with fixtures
    
    Returns:
        MockMongoClient instance
    """
    # Create guild fixtures
    guild_ids = [f"1{i:08d}" for i in range(1, 4)]
    guild_fixtures = create_guild_config_fixtures(len(guild_ids))
    
    # Create user fixtures
    user_ids = [f"2{i:08d}" for i in range(1, 6)]
    user_fixtures = create_user_profile_fixtures(len(user_ids), guild_ids)
    
    # Create other fixtures
    stats_fixtures = create_stats_record_fixtures(20, guild_ids, user_ids)
    error_fixtures = create_error_record_fixtures(15, guild_ids, user_ids)
    canvas_fixtures = create_canvas_data_fixtures(len(guild_ids), guild_ids)
    
    # Create database with collections
    test_db = MockDatabase("discordbot", {
        "guilds": guild_fixtures,
        "users": user_fixtures,
        "stats": stats_fixtures,
        "errors": error_fixtures,
        "canvas": canvas_fixtures
    })
    
    # Create client with database
    client = MockMongoClient(databases={"discordbot": test_db})
    
    return client

# Database setup function for tests
async def setup_test_database():
    """Set up a test database
    
    Returns:
        (MockMongoClient, database) tuple
    """
    client = create_test_database()
    database = client.discordbot
    return client, database