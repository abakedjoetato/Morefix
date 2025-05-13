# Tower of Temptation Discord Bot - Architecture Documentation

This document provides a comprehensive overview of the Tower of Temptation Discord bot's architecture, design patterns, and system components. It serves as a guide for developers to understand how the various parts of the system interact.

## System Overview

The Tower of Temptation Discord bot is a multi-guild, asynchronous Discord bot built on py-cord with the following key features:

1. **Multi-Guild Support**: Handles multiple Discord servers with isolated configurations and data
2. **SFTP Integration**: Connects to SFTP servers to retrieve and process log files
3. **Canvas System**: Provides an interactive pixel canvas for users to collaborate on
4. **Comprehensive Error Handling**: Robust error telemetry and user feedback system
5. **Command Framework**: Modular command design with slash command support
6. **Premium Features**: Guild-based premium features with proper access control
7. **Backward Compatibility**: Compatibility layer for extensions and data migrations

## Core Architecture

The bot follows a layered architecture:

```
┌────────────────────────────────────────────────────────────┐
│                        User Interface                       │
│           (Discord Interactions & Command Responses)        │
└────────────────┬────────────────────────┬─────────────────┘
                 │                        │
┌────────────────▼───────────┐  ┌────────▼─────────────────┐
│     Command Processing     │  │    Interaction Handling   │
│  (Command & Argument Logic)│  │ (Buttons, Menus, Modals)  │
└────────────────┬───────────┘  └────────┬─────────────────┘
                 │                        │
┌────────────────▼────────────────────────▼─────────────────┐
│                     Business Logic                         │
│        (Core Functionality & Feature Implementation)       │
└┬─────────────┬────────────────┬───────────────┬───────────┘
 │             │                │               │
┌▼─────────────▼┐  ┌───────────▼──────┐  ┌─────▼───────────┐
│  Database     │  │  SFTP Connection │  │  Error Handling │
│  Access Layer │  │  & File Handling │  │  & Telemetry    │
└───────────────┘  └──────────────────┘  └─────────────────┘
```

### Key Components

1. **Bot Core (`bot.py`)**: The central bot class that initializes the Discord connection, manages commands, and coordinates the bot's overall functionality.

2. **Command System**: Modular command structure organized in cogs for better separation of concerns:
   - SFTP commands for file operations
   - Canvas commands for pixel placement and viewing
   - Administrative commands for server management
   - Economy and profile commands for user interaction

3. **Utility Modules**:
   - `sftp_connection_pool.py`: Manages SFTP connections
   - `error_telemetry.py`: Tracks and analyzes errors
   - `user_feedback.py`: Generates user-friendly error messages
   - `command_compatibility_layer.py`: Ensures backward compatibility
   - `data_migration.py`: Handles database schema migrations

4. **Database Layer**: MongoDB-based data storage with collections for:
   - Guild configurations
   - User profiles
   - Canvas data
   - Error telemetry
   - Statistics

## Data Flow

### Command Execution Flow

```
User Input → Discord Gateway → Bot Event Handler → Command Parser →
Command Handler → Business Logic → Database/External Services →
Response Formatter → Discord API → User View
```

### Error Handling Flow

```
Exception → Error Handler → Error Telemetry → Error Categorization →
User Feedback Generation → Discord Response → User View
```

### SFTP Integration Flow

```
Command → SFTP Connection Pool → Connection Acquisition →
File Operation → Data Processing → Response Formatting →
Discord Response → User View
```

## Module Relationships

### Core Dependencies

```
bot.py
  ├── config.py (Configuration settings)
  ├── database.py (Database connection)
  ├── utils/*.py (Utility modules)
  └── cogs/*.py (Command modules)
```

### Utility Dependencies

```
utils/
  ├── sftp_connection_pool.py (Depends on: sftp_exceptions.py)
  ├── sftp_helpers.py (Depends on: sftp_connection_pool.py)
  ├── error_telemetry.py (Independent)
  ├── error_handlers.py (Depends on: error_telemetry.py, user_feedback.py)
  ├── user_feedback.py (Independent)
  ├── command_compatibility_layer.py (Independent)
  ├── data_version.py (Independent)
  └── data_migration.py (Depends on: data_version.py)
```

### Cog Dependencies

```
cogs/
  ├── sftp_commands.py (Depends on: sftp_connection_pool.py, sftp_helpers.py)
  ├── canvas_commands.py (Depends on: canvas.py)
  ├── admin_commands.py (Depends on: guild_config.py)
  ├── profile_commands.py (Independent)
  └── error_handling_cog.py (Depends on: error_telemetry.py, error_handlers.py)
```

## Database Schema

### Guild Configuration

```json
{
  "_id": "guild:12345678901234567",
  "guild_id": "12345678901234567",
  "name": "Guild Name",
  "settings": {
    "prefix": "!",
    "language": "en",
    "timezone": "UTC",
    "premium": false
  },
  "integrations": {
    "sftp": {
      "enabled": true,
      "host": "sftp.example.com",
      "port": 22,
      "username": "user",
      "password": "password",
      "base_path": "/logs"
    }
  }
}
```

### User Profile

```json
{
  "_id": "user:12345678901234567",
  "user_id": "12345678901234567",
  "username": "Username",
  "guilds": ["12345678901234567"],
  "stats": {
    "commands_used": 10,
    "canvas_pixels_placed": 50
  },
  "inventory": {
    "credits": 500,
    "colors": ["#FF0000", "#00FF00"]
  }
}
```

### Canvas Data

```json
{
  "_id": "canvas:12345678901234567",
  "guild_id": "12345678901234567",
  "size": 32,
  "default_color": "#FFFFFF",
  "pixels": {
    "5,5": {
      "color": "#FF0000",
      "user_id": "12345678901234567",
      "timestamp": "2025-05-01T12:00:00Z"
    }
  }
}
```

### Error Telemetry

```json
{
  "_id": "error:abcdef1234567890",
  "id": "abcdef1234567890",
  "timestamp": "2025-05-01T12:00:00Z",
  "category": "sftp",
  "error_type": "ConnectionError",
  "error_message": "Connection refused",
  "fingerprint": "sftp:connection:1",
  "context": {
    "guild_id": "12345678901234567",
    "user_id": "12345678901234567"
  }
}
```

## Key Design Patterns

### Connection Pool Pattern

Used in the SFTP connection management to efficiently handle multiple connections while ensuring thread safety and connection limits.

```python
# Example usage
async with SFTPConnectionPool.get_connection(guild_id) as connection:
    # Use connection
    files = await connection.list_dir(path)
```

### Repository Pattern

Used for database access, abstracting database operations from the business logic.

```python
# Example usage
guild_config = await GuildConfig.get(guild_id)
await guild_config.update(settings=new_settings)
```

### Decorator Pattern

Used for command definitions, error handling, and permission checks.

```python
# Example usage
@commands.command()
@error_handler_middleware
@requires_premium
async def premium_command(ctx):
    # Command implementation
```

### Factory Pattern

Used for creating error responses, embed messages, and other objects.

```python
# Example usage
embed = create_error_embed(
    title="Error",
    description="An error occurred",
    error_type="validation"
)
```

### Strategy Pattern

Used in error handling to dynamically choose the appropriate error handling strategy based on error type.

```python
# Example usage
handler = get_error_handler(error)
await handler.handle(error, context)
```

## Asynchronous Design

The bot extensively uses async/await patterns for all I/O operations:

1. **Discord API Interactions**: All Discord interactions use await for responses
2. **Database Operations**: MongoDB operations are all asynchronous
3. **SFTP Operations**: File transfers and listings use asyncio for concurrency
4. **Background Tasks**: Scheduled tasks run as asyncio background tasks

## Testing Architecture

The testing system uses a mock-based approach:

1. **Discord Mocks**: `tests/discord_mocks.py` provides mock implementations of Discord objects
2. **Database Fixtures**: `tests/test_fixtures.py` provides mock database setup
3. **Command Testing**: `tests/command_tester.py` provides a framework for testing commands
4. **Integration Tests**: Test cases that verify multiple components working together

## Extension Points

The system provides several extension points for developers:

1. **Cog System**: New features can be added via cogs
2. **Command Hooks**: Pre-command and post-command hooks for custom processing
3. **Error Handlers**: Custom error handlers can be registered
4. **Data Migration**: Migration system for extending the database schema

## Security Considerations

1. **SFTP Credentials**: Stored securely in guild configuration
2. **Command Permissions**: Proper permission checks on all commands
3. **Rate Limiting**: Built-in rate limiting for command usage
4. **Data Validation**: Input validation on all command parameters

## Cross-Cutting Concerns

1. **Logging**: Comprehensive logging throughout the application
2. **Error Handling**: Centralized error handling with telemetry
3. **Permissions**: Permission checking framework
4. **Configuration**: Configuration management with defaults

## Performance Considerations

1. **Connection Pooling**: SFTP connections are pooled for efficiency
2. **Caching**: Guild configurations and other frequently accessed data are cached
3. **Background Processing**: Long-running tasks are offloaded to background tasks
4. **Efficient Queries**: Database queries are optimized with proper indexing

## Deployment Architecture

The bot can be deployed as a standalone Python application:

1. **Dependencies**: Python 3.8+, MongoDB, asyncio, py-cord
2. **Configuration**: Environment variables or config file
3. **Database**: MongoDB database for persistence
4. **Hosting**: Can be hosted on any platform that supports Python

---

This architecture documentation provides a high-level overview of the Tower of Temptation Discord bot. For more detailed information on specific components, refer to the individual module documentation and code comments.