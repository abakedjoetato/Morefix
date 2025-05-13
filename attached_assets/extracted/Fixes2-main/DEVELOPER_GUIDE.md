# Tower of Temptation Discord Bot - Developer Guide

This guide provides information and best practices for developers working on or extending the Tower of Temptation Discord bot. Follow these guidelines to ensure your code integrates well with the existing codebase.

## Table of Contents

1. [Development Environment](#development-environment)
2. [Code Style and Standards](#code-style-and-standards)
3. [Project Structure](#project-structure)
4. [Adding New Commands](#adding-new-commands)
5. [Working with the Database](#working-with-the-database)
6. [SFTP Integration](#sftp-integration)
7. [Error Handling](#error-handling)
8. [Testing](#testing)
9. [Documentation](#documentation)
10. [Backward Compatibility](#backward-compatibility)
11. [Common Pitfalls](#common-pitfalls)

## Development Environment

### Required Software

- Python 3.8 or higher
- MongoDB (local or remote instance)
- Git for version control
- A code editor with Python support (e.g., VSCode, PyCharm)

### Setting Up

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tower-of-temptation-bot.git
   cd tower-of-temptation-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   DISCORD_TOKEN=your_bot_token
   MONGODB_URI=mongodb://localhost:27017/towerbot
   ```

5. Run the bot:
   ```bash
   python main.py
   ```

## Code Style and Standards

### Python Conventions

- Follow PEP 8 style guide
- Use 4 spaces for indentation (no tabs)
- Maximum line length of 100 characters
- Use descriptive variable and function names

### Docstrings

All modules, classes, and functions should have docstrings in the following format:

```python
def example_function(param1, param2):
    """Short description of the function.
    
    More detailed explanation if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When and why this exception is raised
    """
    # Function implementation
```

### Type Hints

Use type hints for all function parameters and return values:

```python
def calculate_total(items: List[Dict[str, Any]]) -> int:
    """Calculate the total value of items."""
    return sum(item.get("value", 0) for item in items)
```

### Imports

Organize imports in the following order, with a blank line between groups:

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
import os
import sys
from typing import Dict, List, Optional

import discord
from discord.ext import commands

from utils.helpers import format_message
from config import Config
```

## Project Structure

The project is organized into several directories:

- **Root Directory**: Contains main entry points and configuration
  - `main.py`: Main entry point
  - `bot.py`: Core bot class
  - `config.py`: Configuration settings
  - `run.py`: Bot runner

- **cogs/**: Command modules organized by functionality
  - `sftp_commands.py`: SFTP-related commands
  - `canvas_commands.py`: Canvas-related commands
  - etc.

- **utils/**: Utility modules and helpers
  - `sftp_connection_pool.py`: SFTP connection management
  - `error_telemetry.py`: Error tracking system
  - etc.

- **models/**: Data models and database interaction
  - `guild_config.py`: Guild configuration model
  - `user_profile.py`: User profile model
  - etc.

- **tests/**: Test cases and testing utilities
  - `command_tester.py`: Command testing framework
  - `discord_mocks.py`: Mock Discord objects
  - etc.

## Adding New Commands

### Creating a New Cog

1. Create a new file in the `cogs` directory:

```python
# cogs/example_commands.py
import discord
from discord.ext import commands
from utils.command_compatibility_layer import compatible_slash_command, respond_to_context

class ExampleCommands(commands.Cog):
    """Example commands for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @compatible_slash_command(
        name="example",
        description="An example command"
    )
    async def example_command(self, ctx):
        """Example command implementation."""
        await respond_to_context(ctx, "This is an example command!")

async def setup(bot):
    await bot.add_cog(ExampleCommands(bot))
```

2. Register the cog in `main.py` or `bot.py`:

```python
async def load_extensions():
    # Other extensions...
    await bot.load_extension("cogs.example_commands")
```

### Command Best Practices

1. **Always use the compatibility layer**:
   ```python
   from utils.command_compatibility_layer import compatible_slash_command, respond_to_context
   ```

2. **Include detailed help**:
   - Command name should be descriptive
   - Include a clear description
   - Document all parameters

3. **Parameter Validation**:
   - Validate all user inputs
   - Provide clear error messages for invalid inputs

4. **Permission Checks**:
   - Use Discord's permission system
   - Check bot permissions before attempting actions
   - For premium features, use `is_premium_guild`

5. **Responses**:
   - Use embeds for complex responses
   - Keep text responses concise
   - Use proper formatting

## Working with the Database

### Accessing the Database

The database is available through the bot instance:

```python
async def my_command(self, ctx):
    # Get a collection
    collection = self.bot.db.my_collection
    
    # Find a document
    document = await collection.find_one({"_id": "some_id"})
    
    # Insert a document
    await collection.insert_one({
        "_id": "new_id",
        "name": "Example",
        "created_at": datetime.datetime.now()
    })
```

### Data Models

Use the provided models for common data:

```python
from models.guild_config import GuildConfig

# Get guild configuration
config = await GuildConfig.get(ctx.guild.id)

# Update a setting
await config.update_setting("premium", True)
```

### Best Practices

1. **Use atomic operations** when possible
2. **Include error handling** for database operations
3. **Validate data** before writing to the database
4. **Use indexes** for frequently queried fields
5. **Don't store sensitive data** in plain text

## SFTP Integration

### Using the Connection Pool

```python
from utils.sftp_connection_pool import SFTPConnectionPool

async def my_sftp_command(self, ctx):
    # Get guild ID
    guild_id = ctx.guild.id
    
    # Get a connection from the pool
    async with SFTPConnectionPool.get_connection(guild_id) as connection:
        # List files in a directory
        files = await connection.list_dir("/logs")
        
        # Download a file
        content = await connection.read_file("/logs/example.log")
```

### Error Handling

SFTP operations can fail for various reasons. Always handle these errors:

```python
from utils.sftp_exceptions import SFTPConnectionError, SFTPAuthenticationError

try:
    async with SFTPConnectionPool.get_connection(guild_id) as connection:
        # SFTP operations...
except SFTPConnectionError as e:
    await ctx.send(f"Failed to connect: {e}")
except SFTPAuthenticationError as e:
    await ctx.send(f"Authentication failed: {e}")
except Exception as e:
    await ctx.send(f"An error occurred: {e}")
```

## Error Handling

### Using the Error Telemetry System

```python
from utils.error_telemetry import ErrorTelemetry
from utils.user_feedback import create_error_embed

async def my_command(self, ctx):
    try:
        # Command implementation...
    except Exception as e:
        # Track the error
        error_id = await ErrorTelemetry.track_error(e, context={
            "guild_id": ctx.guild.id,
            "user_id": ctx.author.id,
            "command": ctx.command.name
        })
        
        # Send user-friendly response
        embed = create_error_embed(
            title="Error",
            description="An error occurred while processing your command.",
            error_type="command",
            error_id=error_id
        )
        
        await ctx.send(embed=embed)
```

### Custom Error Handlers

You can create custom error handlers for specific commands:

```python
@my_command.error
async def my_command_error(self, ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You're missing a required argument!")
    else:
        # Pass to global error handler
        await self.bot.on_command_error(ctx, error)
```

## Testing

### Writing Tests

Create test cases in the `tests/test_suites` directory:

```python
# tests/test_suites/example_tests.py
from tests.command_tester import (
    CommandTestSuite, ResponseValidator,
    create_slash_command_test
)

def create_test_suite():
    suite = CommandTestSuite("Example Tests")
    
    # Add test for example command
    suite.add_test(create_slash_command_test(
        command_name="example",
        validators=[
            ResponseValidator(
                content_contains=["example command"]
            )
        ]
    ))
    
    return suite
```

### Running Tests

```bash
python -m tests.run_tests --all
# Or for specific tests:
python -m tests.run_tests --suite example_tests
```

## Documentation

### Code Documentation

- Document all modules, classes, and functions with docstrings
- Update the README.md when adding new features
- Keep the ARCHITECTURE.md up to date when changing the system design

### User Documentation

- Update command help text when changing commands
- Create user guides for complex features
- Include examples in documentation

## Backward Compatibility

### Using the Compatibility Layer

Always use the compatibility layer for commands:

```python
from utils.command_compatibility_layer import (
    compatible_command, compatible_slash_command, compatible_group,
    normalize_context, respond_to_context
)

@compatible_slash_command(
    name="example",
    description="Example command"
)
async def example_command(self, ctx):
    # Normalize context to handle both regular context and interactions
    context = normalize_context(ctx)
    
    # Get user consistently regardless of context type
    user = context["user"]
    
    # Respond consistently
    await respond_to_context(ctx, f"Hello, {user.name}!")
```

### Data Migrations

When changing database schemas, add a migration:

```python
from utils.data_version import register_migration

# Register a migration for the users collection to version 1.1.0
async def migrate_users_to_1_1_0(context):
    # Migration implementation...
    return True

register_migration("users", "1.1.0", migrate_users_to_1_1_0)
```

## Common Pitfalls

### 1. Not Handling Rate Limits

Discord has rate limits on API calls. Handle them properly:

```python
try:
    await ctx.send("Message")
except discord.HTTPException as e:
    if e.status == 429:  # Rate limited
        retry_after = e.retry_after
        await asyncio.sleep(retry_after)
        await ctx.send("Message")
    else:
        raise
```

### 2. Blocking the Event Loop

Avoid blocking operations in the event loop:

```python
# Bad:
result = some_blocking_operation()

# Good:
result = await asyncio.to_thread(some_blocking_operation)
```

### 3. Not Validating User Input

Always validate user input:

```python
@commands.command()
async def set_color(self, ctx, color: str):
    # Validate the color format
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        await ctx.send("Invalid color format. Use #RRGGBB format.")
        return
    
    # Proceed with the command...
```

### 4. Ignoring Permissions

Check permissions before performing actions:

```python
@commands.command()
@commands.has_permissions(manage_guild=True)
async def admin_command(self, ctx):
    # Only users with "Manage Server" permission can use this
    # ...
```

### 5. Hardcoding Configuration

Use the configuration system instead of hardcoding values:

```python
# Bad:
limit = 100

# Good:
from config import Config
limit = Config.RATE_LIMIT_STANDARD
```

---

This developer guide provides an overview of best practices for developing the Tower of Temptation Discord bot. For more detailed information, refer to the inline documentation and the ARCHITECTURE.md document.