# Pycord 2.6.1 Compatibility Guide

This guide documents all the compatibility layers implemented to ensure the Tower of Temptation Discord bot works properly with Pycord 2.6.1 and maintains backwards compatibility.

## Table of Contents

1. [Introduction](#introduction)
2. [MongoDB Compatibility](#mongodb-compatibility)
3. [Discord API Compatibility](#discord-api-compatibility)
4. [Command System Compatibility](#command-system-compatibility)
5. [Async/Await & Type Safety](#asyncawait--type-safety)
6. [Event System & Intent Compatibility](#event-system--intent-compatibility)
7. [Final Integration](#final-integration)
8. [Troubleshooting](#troubleshooting)

## Introduction

Pycord 2.6.1 introduces several breaking changes that require compatibility layers for seamless integration. This document outlines all the compatibility modules created to address these changes.

## MongoDB Compatibility

### SafeMongoDBResult

The `SafeMongoDBResult` class provides a consistent interface for accessing MongoDB operation results across different versions:

```python
from utils.safe_mongodb import SafeMongoDBResult

# Example usage
result = collection.insert_one(document)
safe_result = SafeMongoDBResult(result)

# Access attributes safely
if safe_result.acknowledged:
    print(f"Inserted document with ID: {safe_result.inserted_id}")
```

### SafeDocument

The `SafeDocument` class provides attribute-style access to MongoDB documents:

```python
from utils.safe_mongodb import SafeDocument, safe_find_one

# Example usage
document = await safe_find_one(collection, {"user_id": 123})
safe_doc = SafeDocument(document)

# Access attributes safely
print(f"User name: {safe_doc.name}")
```

### Collection Access

Use the `get_collection` function for consistent collection access:

```python
from utils.safe_mongodb import get_collection

# Example usage
collection = get_collection(db, "users")
```

### BSON Data Type Handling

The `mongo_compat` module provides utilities for handling BSON data types:

```python
from utils.mongo_compat import serialize_document, deserialize_document

# Example usage
serialized = serialize_document(document)  # Convert for storage
deserialized = deserialize_document(serialized)  # Convert back for use
```

## Discord API Compatibility

### Centralized Imports

Use the `discord_compat` module for all Discord-related imports:

```python
from utils.discord_compat import discord, commands, app_commands
```

### Attribute Access

Use the attribute access helpers for accessing Discord object attributes safely:

```python
from utils.attribute_access import safe_server_getattr, safe_member_getattr

# Example usage
server_name = safe_server_getattr(server, "name", "Unknown Server")
member_id = safe_member_getattr(member, "id")
```

### Interaction Handling

Use the `hybrid_send` function to send messages to either Context or Interaction:

```python
from utils.interaction_handlers import hybrid_send

# Example usage
await hybrid_send(ctx_or_interaction, content="Hello!", ephemeral=True)
```

## Command System Compatibility

### Enhanced Slash Commands

Use the `EnhancedSlashCommand` class for compatible slash commands:

```python
from utils.command_handlers import enhanced_slash_command

# Example usage
@enhanced_slash_command(name="hello", description="A friendly greeting")
async def hello(ctx):
    await ctx.send("Hello!")
```

### Command Options

Use the option builder functions for command parameters:

```python
from utils.command_handlers import text_option, integer_option

# Example usage
@enhanced_slash_command(name="echo")
async def echo(ctx, text=text_option("text", "Text to echo", required=True)):
    await ctx.send(text)
```

### Command Builder

Use the `CommandBuilder` for more complex commands:

```python
from utils.command_parameter_builder import CommandBuilder

# Example usage
builder = CommandBuilder(
    name="test",
    description="Test command",
    callback=my_callback_function
)
builder.add_string_parameter(name="text", description="Text to display")
command = builder.build()
```

## Async/Await & Type Safety

### Async Helpers

Use the async helpers for better async function handling:

```python
from utils.async_helpers import ensure_async, ensure_sync, safe_gather

# Example usage
sync_func_as_async = ensure_async(sync_function)
result = await sync_func_as_async()

results = await safe_gather(coro1(), coro2(), return_exceptions=True)
```

### AsyncCache

Use the `AsyncCache` for caching async function results:

```python
from utils.async_helpers import AsyncCache, cached_async

# Example usage
cache = AsyncCache(ttl=300.0)  # 5 minutes TTL

@cached_async(ttl=300.0)
async def fetch_data(user_id):
    # Expensive operation
    return data
```

### Type Safety

Use the type safety utilities for safer type handling:

```python
from utils.type_safety import safe_cast, safe_int, safe_str

# Example usage
user_id = safe_int(user_id_str, default=0)
username = safe_str(username_obj, max_length=32)
```

## Event System & Intent Compatibility

### Intent Helpers

Use the intent helpers for compatible Discord intents:

```python
from utils.intent_helpers import get_default_intents, create_intents

# Example usage
intents = get_default_intents()  # Get default intents with message_content
custom_intents = create_intents(guilds=True, members=True, guild_messages=True)
```

### Permission Helpers

Use the permission helpers for handling Discord permissions:

```python
from utils.permission_helpers import has_permission, format_permissions

# Example usage
if has_permission(member.guild_permissions, "manage_messages"):
    # Allow the action
    pass

perm_text = format_permissions(member.guild_permissions)
```

### Event Dispatcher

Use the `CompatibleBot` for better event handling:

```python
from utils.event_helpers import CompatibleBot

# Example usage
bot = CompatibleBot(command_prefix="!", intents=intents)

@bot.event
async def on_message(message):
    # Handle message
    pass
```

## Final Integration

To fully integrate all compatibility layers:

1. Replace Discord imports with `discord_compat` imports
2. Use `SafeMongoDBResult` for MongoDB operations
3. Use attribute access helpers for Discord objects
4. Use enhanced slash commands for app commands
5. Use async helpers for asynchronous code
6. Use type safety utilities for safer type handling
7. Use intent and permission helpers for Discord intents and permissions

## Troubleshooting

If you encounter issues with the compatibility layers:

1. Check the import paths for compatibility modules
2. Ensure all MongoDB operations use the safe result wrapper
3. Verify attribute access uses the safe attribute helpers
4. Review Discord API calls for proper interaction handling
5. Run the comprehensive test suite with `python test_compatibility.py`

For specific component issues, refer to the detailed implementation in the corresponding module:

- MongoDB issues: `utils/safe_mongodb.py` and `utils/mongo_compat.py`
- Discord API issues: `utils/discord_compat.py` and `utils/attribute_access.py`
- Command issues: `utils/command_handlers.py` and `utils/command_parameter_builder.py`
- Async issues: `utils/async_helpers.py`
- Type issues: `utils/type_safety.py`
- Event issues: `utils/event_helpers.py`
- Intent/Permission issues: `utils/intent_helpers.py` and `utils/permission_helpers.py`