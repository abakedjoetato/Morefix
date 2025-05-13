# py-cord 2.6.1 Compatibility Guide

This document explains the fixes and compatibility solutions implemented for py-cord 2.6.1 in the Tower of Temptation Discord bot.

## Core Issues Fixed

### 1. SlashCommand._parse_options Method

The original issue causing "'list' object has no attribute 'items'" has been fixed by properly subclassing SlashCommand and overriding the _parse_options method. This ensures correct parameter handling for both list-style options (used in newer py-cord versions) and dict-style options (used in older versions).

### 2. Option Type Annotations

Fixed LSP typing issues with option annotations by:
- Separating parameter definitions from type annotations
- Using a parameter builder approach instead of inline option definitions
- Applying options after function definition using the add_parameter_options helper

### 3. Command Registration

Ensured proper command registration by:
- Properly handling command signatures with context parameters
- Creating properly typed subclasses of SlashCommand
- Properly forwarding parameters to parent class implementations

### 4. Premium Feature Verification

Enhanced the premium verification system to:
- Use proper guild-based verification (never user-based)
- Support tier-based access control with feature mapping
- Implement safe database access with proper error handling
- Replace monkey patching with proper import proxies

## File Structure

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

### Defining Slash Commands

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