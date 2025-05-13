# py-cord 2.6.1 Compatibility Guide

This document explains the fixes and compatibility solutions implemented for py-cord 2.6.1 in the Tower of Temptation Discord bot.

## Core Issues Fixed

### 1. Command Compatibility

#### SlashCommand._parse_options Method

The original issue causing "'list' object has no attribute 'items'" has been fixed by properly subclassing SlashCommand and overriding the _parse_options method. This ensures correct parameter handling for both list-style options (used in newer py-cord versions) and dict-style options (used in older versions).

#### Option Type Annotations

Fixed LSP typing issues with option annotations by:
- Separating parameter definitions from type annotations
- Using a parameter builder approach instead of inline option definitions
- Applying options after function definition using the add_parameter_options helper

#### Command Registration

Ensured proper command registration by:
- Properly handling command signatures with context parameters
- Creating properly typed subclasses of SlashCommand
- Properly forwarding parameters to parent class implementations

#### Command Decorator Compatibility

Added compatibility decorators for seamless usage across versions:
- `command()` - Unified decorator for registering commands
- `describe()` - Unified decorator for parameter descriptions
- `guild_only()` - Unified decorator for guild-only commands

### 2. Discord API Compatibility

#### Interaction Response Handling

Added compatibility layer for interaction responses:
- `safely_respond_to_interaction()` - Safe response function with fallbacks
- `hybrid_send()` - Unified sending function for both Context and Interaction

#### Attribute Access Safety

Implemented safer attribute access in event handlers:
- Using `getattr()` with proper defaults for server object attributes
- Proper exception handling for Discord gateway events

### 3. MongoDB Compatibility

#### Collection Access Pattern

Fixed collection access pattern with compatibility handling:
- Added `get_collection()` method with multiple access pattern support
- Dictionary-style, property-style, and method-style access compatibility
- Proper error handling for collection access failures

#### MongoDB Result Handling

Implemented `SafeMongoDBResult` for consistent result access:
- Property access compatibility across Motor and PyMongo
- Consistent method naming and behavior across versions
- Boolean evaluation for simplified success checking

#### BSON Data Types Handling

Added specialized handling for BSON data types:
- Safe conversion of MongoDB DateTime types to Python datetime
- Serialization and deserialization with type compatibility
- Nested BSON type handling for complex documents

### 4. Premium Feature Verification

Enhanced the premium verification system to:
- Use proper guild-based verification (never user-based)
- Support tier-based access control with feature mapping
- Implement safe database access with proper error handling
- Replace monkey patching with proper import proxies

## File Structure

### Discord API Compatibility

- **utils/discord_compat.py**: Main compatibility layer for Discord API functionality
- **utils/interaction_handlers.py**: Compatibility for interaction responses
- **cogs/setup_fixed.py**: Fixed version of setup commands with proper decorators
- **cogs/help.py**: Fixed help command system with async/await correctness

### MongoDB Compatibility

- **utils/safe_mongodb.py**: Safe MongoDB document handling with compatibility
- **utils/mongo_compat.py**: Utilities for BSON data type compatibility
- **test_safe_mongodb_compat.py**: Tests for MongoDB compatibility layers
- **test_mongo_compat.py**: Tests for BSON data type compatibility

### Command System Fixes

- **utils/command_handlers.py**: Implements EnhancedSlashCommand with proper _parse_options method
- **utils/command_imports.py**: Safely imports command components with version detection
- **utils/command_parameter_builder.py**: Builds command parameters without LSP typing issues
- **utils/command_examples.py**: Demonstrates proper usage of the enhanced system

### Database Access Improvements

- **utils/safe_database.py**: Provides safe database operations with proper error handling

### Premium System Improvements

- **utils/premium_verification.py**: Core premium feature verification system
- **utils/premium_import_proxy.py**: Clean import interface for backward compatibility
- **utils/exceptions.py**: Custom exceptions for premium-related errors

### Error Handling

- Improved error handling in bot.py for both standard and application commands
- Added structured exception system in utils/exceptions.py
- Enhanced error messages for premium access failures

## Usage Examples

### Discord Compatibility Layer

```python
# Import unified decorators
from utils.discord_compat import command, describe, guild_only

class MyCog(commands.Cog):
    @command()
    @describe(option1="First option", option2="Second option")
    @guild_only()
    async def my_command(self, ctx, option1=None, option2=None):
        # Command implementation that works on all versions
        pass
```

### Interaction Response Handling

```python
from utils.interaction_handlers import safely_respond_to_interaction, hybrid_send

# Handle interactions safely
async def handle_interaction(interaction):
    # Works with both responded and new interactions
    await safely_respond_to_interaction(
        interaction,
        content="Response content",
        embed=embed,
        ephemeral=True
    )
    
# Send messages to either Context or Interaction
async def send_response(ctx_or_interaction):
    # Works with both command Context and Interactions
    await hybrid_send(
        ctx_or_interaction,
        content="Response content",
        embed=embed
    )
```

### Safe MongoDB Document Handling

```python
from utils.safe_mongodb import SafeDocument
from utils.mongo_compat import safe_serialize_for_mongodb

class Guild(SafeDocument):
    collection_name = "guilds"
    
    def __init__(self, _id=None, name=None, settings=None):
        super().__init__(_id)
        self.name = name
        self.settings = settings or {}
        
    # These methods automatically use the compatibility layers
    async def save(self):
        await super().save()
        
    @classmethod
    async def get_by_guild_id(cls, guild_id):
        # Handles collection access consistently across versions
        # Also deserializes BSON types correctly
        return await cls.find_one({"_id": str(guild_id)})
```

### Enhanced Slash Commands

```python
@enhanced_slash_command(
    name="example_command",
    description="Example command description"
)
async def example_command(self, ctx, param1=None, param2=None):
    # Command implementation
    pass

# Add parameters separately
add_parameter_options(example_command, {
    'param1': text_option(name="param1", description="First parameter", required=True),
    'param2': number_option(name="param2", description="Second parameter", required=False)
})
```

### Premium Feature Access

```python
from utils.premium_verification import premium_feature_required

@enhanced_slash_command(
    name="premium_feature",
    description="A premium feature command"
)
@premium_feature_required("feature_name")
async def premium_feature_command(self, ctx):
    # Command implementation that requires premium access
    pass
```

### Safe Database Access

```python
from utils.safe_database import get_document_safely, safely_update_document

async def safe_db_operation(db, guild_id):
    # Safely get a document
    guild_doc = await get_document_safely(db.guilds, {"guild_id": str(guild_id)})
    
    if guild_doc:
        # Safely update a document
        await safely_update_document(
            db.guilds,
            {"guild_id": str(guild_id)},
            {"$set": {"last_accessed": datetime.now()}}
        )
```

## Implementation Notes

1. All fixes follow proper OOP principles and avoid monkey patching
2. The implementation is scalable across multiple guilds and SFTP contexts
3. Premium checks remain strictly guild-scoped, never user-based
4. Error handling is comprehensive and user-friendly
5. Code is properly documented with docstrings