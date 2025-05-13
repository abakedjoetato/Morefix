"""
Command Compatibility Layer for Tower of Temptation PvP Statistics Bot

This module provides backward compatibility for commands:
1. Compatibility decorators for different Discord.py/py-cord versions
2. Command parameter normalization
3. Consistent behavior across versions
4. Legacy command signature support

This ensures a smooth transition for custom extensions and plugins.
"""
import functools
import inspect
import logging
import warnings
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, overload

# Setup logger
logger = logging.getLogger(__name__)

# Type variables for better type hints
T = TypeVar('T')
CommandCallback = TypeVar('CommandCallback', bound=Callable[..., Any])
DecoratedCommand = TypeVar('DecoratedCommand')

# Version compatibility
try:
    import discord
    from discord import app_commands
    from discord.ext import commands
    
    # Determine which version of discord.py/py-cord we're using
    if hasattr(discord, 'version_info'):
        DISCORD_VERSION = discord.version_info
        IS_PYCORD = False
    else:
        # This is most likely py-cord
        IS_PYCORD = True
        # Try to determine version from other attributes
        DISCORD_VERSION = getattr(discord, '__version__', '0.0.0')
    
    logger.info(f"Using {'py-cord' if IS_PYCORD else 'discord.py'} version {DISCORD_VERSION}")
    
except ImportError:
    logger.warning("Discord library not available, compatibility layer will use mock objects")
    # Create mock objects for testing or when discord is not available
    class MockDiscord:
        class app_commands:
            class Command:
                pass
            
            class Group:
                pass
            
            class CommandTree:
                pass
    
        class ext:
            class commands:
                class Command:
                    pass
                
                class Group:
                    pass
                
                class Cog:
                    pass
    
    discord = MockDiscord()
    app_commands = discord.app_commands
    commands = discord.ext.commands
    
    IS_PYCORD = False
    DISCORD_VERSION = '0.0.0'

# Compatibility constants
SUPPORTS_ASYNC_SETUP = IS_PYCORD or (not IS_PYCORD and DISCORD_VERSION >= (2, 0, 0))
SUPPORTS_APP_COMMANDS = IS_PYCORD or (not IS_PYCORD and DISCORD_VERSION >= (2, 0, 0))

# Utility functions
def get_command_signature(command: Any) -> str:
    """Get the signature of a command, handling different versions
    
    Args:
        command: The command to get the signature for
        
    Returns:
        The command signature as a string
    """
    if hasattr(command, 'qualified_name'):
        name = command.qualified_name
    else:
        name = getattr(command, 'name', str(command))
    
    # Get parameters
    if hasattr(command, 'callback'):
        params = inspect.signature(command.callback).parameters
    else:
        params = getattr(command, 'params', {})
    
    # Format parameters
    param_str = ''
    if params:
        param_list = []
        for param_name, param in params.items():
            if param_name in ('self', 'ctx', 'context', 'interaction'):
                continue
            
            if param.default is not param.empty:
                param_list.append(f"[{param_name}={param.default}]")
            elif param.kind == param.VAR_POSITIONAL:
                param_list.append(f"[{param_name}...]")
            elif param.kind == param.VAR_KEYWORD:
                param_list.append(f"[**{param_name}]")
            else:
                param_list.append(f"<{param_name}>")
        
        param_str = ' ' + ' '.join(param_list)
    
    return f"{name}{param_str}"

def check_signature_compatibility(old_command: Any, new_command: Any) -> Tuple[bool, List[str]]:
    """Check if two command signatures are compatible
    
    Args:
        old_command: The old command
        new_command: The new command
        
    Returns:
        Tuple of (is_compatible, list of incompatibilities)
    """
    # Get parameters for both commands
    if hasattr(old_command, 'callback'):
        old_params = inspect.signature(old_command.callback).parameters
    else:
        old_params = getattr(old_command, 'params', {})
    
    if hasattr(new_command, 'callback'):
        new_params = inspect.signature(new_command.callback).parameters
    else:
        new_params = getattr(new_command, 'params', {})
    
    # Filter out context parameters
    old_params = {k: v for k, v in old_params.items() 
                 if k not in ('self', 'ctx', 'context', 'interaction')}
    new_params = {k: v for k, v in new_params.items() 
                 if k not in ('self', 'ctx', 'context', 'interaction')}
    
    # Check if compatible
    incompatibilities = []
    
    # Check for missing required parameters
    for param_name, param in old_params.items():
        if param_name not in new_params and param.default is param.empty:
            incompatibilities.append(f"Required parameter '{param_name}' from old command missing in new command")
    
    # Check for new required parameters
    for param_name, param in new_params.items():
        if param_name not in old_params and param.default is param.empty:
            incompatibilities.append(f"New command has additional required parameter '{param_name}'")
    
    # Check for parameter type changes
    for param_name, old_param in old_params.items():
        if param_name in new_params:
            new_param = new_params[param_name]
            
            # Check if parameter kind changed (e.g. positional to keyword)
            if old_param.kind != new_param.kind:
                incompatibilities.append(f"Parameter '{param_name}' changed kind from {old_param.kind} to {new_param.kind}")
            
            # Check if annotation changed (if present)
            if (old_param.annotation is not inspect.Parameter.empty and
                new_param.annotation is not inspect.Parameter.empty and
                old_param.annotation != new_param.annotation):
                incompatibilities.append(f"Parameter '{param_name}' changed type from {old_param.annotation} to {new_param.annotation}")
    
    return len(incompatibilities) == 0, incompatibilities

# Compatibility decorators
def compatible_command(
    *args, 
    name: Optional[str] = None, 
    legacy_aliases: Optional[List[str]] = None,
    **kwargs
) -> Callable[[CommandCallback], DecoratedCommand]:
    """Decorator for creating commands compatible with both discord.py and py-cord
    
    Args:
        *args: Arguments to pass to the command decorator
        name: Name of the command
        legacy_aliases: Aliases for backward compatibility
        **kwargs: Keyword arguments to pass to the command decorator
        
    Returns:
        Decorated command
    """
    def decorator(func: CommandCallback) -> DecoratedCommand:
        # Store original function
        func.__original_function__ = func
        
        # Add compatibility metadata
        func.__compatibility_info__ = {
            'name': name or func.__name__,
            'legacy_aliases': legacy_aliases or [],
            'is_compatible_command': True
        }
        
        # Use the appropriate decorator based on version
        if IS_PYCORD:
            # py-cord
            if legacy_aliases:
                kwargs['aliases'] = legacy_aliases
            
            decorated = commands.command(*args, name=name, **kwargs)(func)
        else:
            # discord.py
            if legacy_aliases:
                kwargs['aliases'] = legacy_aliases
                
            decorated = commands.command(*args, name=name, **kwargs)(func)
        
        # Store compatibility info on the decorated command
        decorated.__compatibility_info__ = func.__compatibility_info__
        
        return decorated
    
    return decorator

def compatible_group(
    *args, 
    name: Optional[str] = None, 
    legacy_aliases: Optional[List[str]] = None,
    **kwargs
) -> Callable[[CommandCallback], DecoratedCommand]:
    """Decorator for creating command groups compatible with both discord.py and py-cord
    
    Args:
        *args: Arguments to pass to the group decorator
        name: Name of the group
        legacy_aliases: Aliases for backward compatibility
        **kwargs: Keyword arguments to pass to the group decorator
        
    Returns:
        Decorated command group
    """
    def decorator(func: CommandCallback) -> DecoratedCommand:
        # Store original function
        func.__original_function__ = func
        
        # Add compatibility metadata
        func.__compatibility_info__ = {
            'name': name or func.__name__,
            'legacy_aliases': legacy_aliases or [],
            'is_compatible_group': True
        }
        
        # Use the appropriate decorator based on version
        if IS_PYCORD:
            # py-cord
            if legacy_aliases:
                kwargs['aliases'] = legacy_aliases
                
            decorated = commands.group(*args, name=name, **kwargs)(func)
        else:
            # discord.py
            if legacy_aliases:
                kwargs['aliases'] = legacy_aliases
                
            decorated = commands.group(*args, name=name, **kwargs)(func)
        
        # Store compatibility info on the decorated group
        decorated.__compatibility_info__ = func.__compatibility_info__
        
        return decorated
    
    return decorator

def compatible_slash_command(
    *args,
    name: Optional[str] = None,
    description: Optional[str] = None,
    guild_only: bool = False,
    **kwargs
) -> Callable[[CommandCallback], DecoratedCommand]:
    """Decorator for creating slash commands compatible with both discord.py and py-cord
    
    Args:
        *args: Arguments to pass to the command decorator
        name: Name of the slash command
        description: Description of the slash command
        guild_only: Whether the command is restricted to guilds
        **kwargs: Keyword arguments to pass to the command decorator
        
    Returns:
        Decorated slash command
    """
    def decorator(func: CommandCallback) -> DecoratedCommand:
        # Store original function
        func.__original_function__ = func
        
        # Add compatibility metadata
        func.__compatibility_info__ = {
            'name': name or func.__name__,
            'description': description or func.__doc__ or "No description",
            'guild_only': guild_only,
            'is_compatible_slash_command': True
        }
        
        # Handle different library versions
        if not SUPPORTS_APP_COMMANDS:
            # Legacy version without slash commands - create a regular command and add a warning
            warnings.warn(f"Slash command '{name or func.__name__}' created as regular command due to Discord library version")
            decorated = commands.command(*args, name=name, **kwargs)(func)
        elif IS_PYCORD:
            # py-cord
            decorated = discord.slash_command(
                *args, 
                name=name, 
                description=description or func.__doc__ or "No description",
                guild_only=guild_only,
                **kwargs
            )(func)
        else:
            # discord.py 2.0+
            # Note: This won't directly register the command - that happens during tree syncing
            @functools.wraps(func)
            async def wrapper(self, interaction, *args_inner, **kwargs_inner):
                return await func(self, interaction, *args_inner, **kwargs_inner)
            
            # Add attributes that app_commands.command would add
            wrapper.name = name or func.__name__
            wrapper.description = description or func.__doc__ or "No description"
            wrapper.guild_only = guild_only
            decorated = wrapper
        
        # Store compatibility info on the decorated command
        decorated.__compatibility_info__ = func.__compatibility_info__
        
        return decorated
    
    return decorator

def compatible_cog_setup(legacy_add_cog: bool = True) -> Callable[[Callable], Callable]:
    """Decorator for cog setup function to support both async and sync setup
    
    Args:
        legacy_add_cog: Whether to support legacy add_cog in setup function
        
    Returns:
        Decorated setup function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(bot):
            """Synchronous setup for older Discord.py versions"""
            cog = func(bot)
            if legacy_add_cog and cog is not None:
                bot.add_cog(cog)
            return cog
        
        @functools.wraps(func)
        async def async_wrapper(bot):
            """Asynchronous setup for py-cord or Discord.py 2.0+"""
            cog = await func(bot)
            if legacy_add_cog and cog is not None:
                await bot.add_cog(cog)
            return cog
        
        # Use the appropriate wrapper based on version
        wrapper = async_wrapper if SUPPORTS_ASYNC_SETUP else sync_wrapper
        
        # Store original function and compatibility info
        wrapper.__original_function__ = func
        wrapper.__compatibility_info__ = {
            'is_compatible_setup': True,
            'supports_async': SUPPORTS_ASYNC_SETUP,
            'legacy_add_cog': legacy_add_cog
        }
        
        return wrapper
    
    return decorator

# Parameter handling
def normalize_context(
    ctx_or_interaction: Any
) -> Dict[str, Any]:
    """Normalize context object to a standard dictionary
    
    Works with both command context and interaction objects
    
    Args:
        ctx_or_interaction: Context or interaction object
        
    Returns:
        Dictionary with normalized context attributes
    """
    normalized = {}
    
    # Check which type of context we have
    if hasattr(ctx_or_interaction, 'interaction'):
        # This is a modern Context with Interaction
        normalized['context_type'] = 'hybrid'
        normalized['interaction'] = ctx_or_interaction.interaction
        normalized['bot'] = ctx_or_interaction.bot
        normalized['guild'] = ctx_or_interaction.guild
        normalized['channel'] = ctx_or_interaction.channel
        normalized['author'] = ctx_or_interaction.author
        normalized['user'] = ctx_or_interaction.author
        normalized['message'] = getattr(ctx_or_interaction, 'message', None)
        normalized['command'] = ctx_or_interaction.command
        
        # Add interaction-specific attributes
        if ctx_or_interaction.interaction:
            normalized['options'] = getattr(ctx_or_interaction.interaction, 'options', {})
            normalized['data'] = getattr(ctx_or_interaction.interaction, 'data', {})
        
    elif hasattr(ctx_or_interaction, 'guild_id'):
        # This is an Interaction
        normalized['context_type'] = 'interaction'
        normalized['interaction'] = ctx_or_interaction
        normalized['bot'] = getattr(ctx_or_interaction, 'client', None) or getattr(ctx_or_interaction, 'bot', None)
        normalized['guild'] = getattr(ctx_or_interaction, 'guild', None)
        normalized['guild_id'] = ctx_or_interaction.guild_id
        normalized['channel'] = getattr(ctx_or_interaction, 'channel', None)
        normalized['channel_id'] = getattr(ctx_or_interaction, 'channel_id', None)
        normalized['user'] = getattr(ctx_or_interaction, 'user', None)
        normalized['author'] = normalized['user']
        normalized['message'] = None
        normalized['command'] = getattr(ctx_or_interaction, 'command', None)
        normalized['options'] = getattr(ctx_or_interaction, 'options', {})
        normalized['data'] = getattr(ctx_or_interaction, 'data', {})
        
    else:
        # This is a Context
        normalized['context_type'] = 'context'
        normalized['interaction'] = None
        normalized['bot'] = ctx_or_interaction.bot
        normalized['guild'] = ctx_or_interaction.guild
        normalized['guild_id'] = getattr(ctx_or_interaction.guild, 'id', None)
        normalized['channel'] = ctx_or_interaction.channel
        normalized['channel_id'] = getattr(ctx_or_interaction.channel, 'id', None)
        normalized['author'] = ctx_or_interaction.author
        normalized['user'] = ctx_or_interaction.author
        normalized['message'] = getattr(ctx_or_interaction, 'message', None)
        normalized['command'] = ctx_or_interaction.command
        normalized['options'] = {}
        normalized['data'] = {}
    
    # Add helper methods
    normalized['get_option'] = lambda name, default=None: (
        normalized['options'].get(name, default) 
        if isinstance(normalized['options'], dict) 
        else default
    )
    
    return normalized

# Response helpers
async def respond_to_context(
    ctx_or_interaction: Any,
    content: Optional[str] = None,
    embed: Optional[Any] = None,
    file: Optional[Any] = None,
    files: Optional[List[Any]] = None,
    ephemeral: bool = False,
    **kwargs
) -> Any:
    """Respond to a context/interaction in a version-compatible way
    
    Args:
        ctx_or_interaction: Context or interaction object
        content: Text content to send
        embed: Embed to send
        file: File to send
        files: Files to send
        ephemeral: Whether the response should be ephemeral
        **kwargs: Additional keyword arguments for the response
        
    Returns:
        Response object (message or interaction response)
    """
    # Normalize context to get context type
    normalized = normalize_context(ctx_or_interaction)
    context_type = normalized['context_type']
    
    try:
        if context_type == 'interaction':
            # This is an Interaction
            if hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'send_message'):
                # Modern Interaction
                await ctx_or_interaction.response.send_message(
                    content=content,
                    embed=embed,
                    file=file,
                    files=files,
                    ephemeral=ephemeral,
                    **kwargs
                )
                return await ctx_or_interaction.original_response()
            else:
                # py-cord Interaction
                return await ctx_or_interaction.send(
                    content=content,
                    embed=embed,
                    file=file,
                    files=files,
                    ephemeral=ephemeral,
                    **kwargs
                )
        elif context_type == 'hybrid':
            # This is a Context with Interaction
            if normalized['interaction'] and not normalized['interaction'].response.is_done():
                # Respond to the interaction
                await normalized['interaction'].response.send_message(
                    content=content,
                    embed=embed,
                    file=file,
                    files=files,
                    ephemeral=ephemeral,
                    **kwargs
                )
                return await normalized['interaction'].original_response()
            else:
                # Respond to the context
                return await ctx_or_interaction.send(
                    content=content,
                    embed=embed,
                    file=file,
                    files=files,
                    **kwargs
                )
        else:
            # This is a Context
            return await ctx_or_interaction.send(
                content=content,
                embed=embed,
                file=file,
                files=files,
                **kwargs
            )
    except Exception as e:
        logger.error(f"Error responding to context: {type(e).__name__}: {e}")
        # Fallback
        try:
            if hasattr(ctx_or_interaction, 'send'):
                return await ctx_or_interaction.send(
                    content=content or "Error processing command",
                    embed=embed,
                    file=file,
                    files=files,
                    **kwargs
                )
            else:
                logger.error("Could not respond to context - no suitable method found")
                return None
        except Exception as e2:
            logger.error(f"Fallback error response failed: {type(e2).__name__}: {e2}")
            return None

# Utilities for command migration documentation
def generate_migration_notes() -> str:
    """Generate notes on migrating commands to the latest version
    
    Returns:
        Markdown formatted migration guide
    """
    notes = """# Command Migration Guide

## Overview

This guide covers migrating command code to be compatible with the latest 
version of the bot framework. The compatibility layer handles most
differences between Discord.py and py-cord, but some changes may still
be required.

## Key Changes

1. **Context vs Interaction**: Commands can now receive either Context or Interaction objects
2. **Parameter Handling**: Parameter types and defaults may differ between versions
3. **Response Methods**: Different methods for responding to commands
4. **Cog Setup**: Now supports both sync and async setup functions

## Using the Compatibility Layer

The compatibility layer provides several decorators and utilities:

- `@compatible_command()`: For regular text commands
- `@compatible_slash_command()`: For slash commands
- `@compatible_group()`: For command groups
- `@compatible_cog_setup()`: For cog setup functions
- `normalize_context()`: Convert context to a standard format
- `respond_to_context()`: Send responses in a compatible way

## Migration Examples

### Before:

```python
@commands.command()
async def hello(self, ctx):
    await ctx.send("Hello, world!")
```

### After:

```python
from utils.command_compatibility_layer import compatible_command, respond_to_context

@compatible_command()
async def hello(self, ctx):
    await respond_to_context(ctx, "Hello, world!")
```

### Slash Command Example:

```python
from utils.command_compatibility_layer import compatible_slash_command, respond_to_context

@compatible_slash_command(
    name="hello",
    description="Say hello to the bot"
)
async def hello_slash(self, interaction):
    await respond_to_context(interaction, "Hello from slash command!")
```

## Best Practices

1. Use the compatibility decorators for all commands
2. Use `normalize_context()` to handle both interaction and context objects
3. Use `respond_to_context()` instead of direct send methods
4. Test commands with both Discord.py and py-cord if possible
5. Check the compatibility of parameter types and defaults

## Additional Resources

- Compatibility layer documentation
- Discord.py documentation
- py-cord documentation
"""
    return notes

def generate_command_upgrade_report(commands_list: List[Any]) -> str:
    """Generate a report on upgrading commands to the latest version
    
    Args:
        commands_list: List of command objects to analyze
        
    Returns:
        Markdown formatted report
    """
    report = "# Command Upgrade Report\n\n"
    report += "This report analyzes commands for compatibility with the latest version.\n\n"
    
    # Group commands by compatibility status
    compatible = []
    needs_upgrade = []
    
    for cmd in commands_list:
        # Check if already has compatibility info
        if hasattr(cmd, '__compatibility_info__'):
            compatible.append(cmd)
        else:
            needs_upgrade.append(cmd)
    
    # Report on compatible commands
    report += f"## Already Compatible ({len(compatible)})\n\n"
    if compatible:
        for cmd in compatible:
            info = getattr(cmd, '__compatibility_info__', {})
            cmd_type = "Group" if info.get('is_compatible_group') else "Command"
            if info.get('is_compatible_slash_command'):
                cmd_type = "Slash Command"
            report += f"- **{info.get('name', cmd.name)}** ({cmd_type})\n"
    else:
        report += "No commands are currently using the compatibility layer.\n"
    
    # Report on commands needing upgrade
    report += f"\n## Needs Upgrade ({len(needs_upgrade)})\n\n"
    if needs_upgrade:
        for cmd in needs_upgrade:
            cmd_name = getattr(cmd, 'name', str(cmd))
            cmd_type = "Group" if isinstance(cmd, commands.Group) else "Command"
            if hasattr(cmd, 'is_slash_command') and cmd.is_slash_command:
                cmd_type = "Slash Command"
            report += f"- **{cmd_name}** ({cmd_type}): Needs compatibility decorator\n"
    else:
        report += "All commands are currently using the compatibility layer.\n"
    
    # Add recommendations
    report += "\n## Recommendations\n\n"
    report += "1. Apply the appropriate compatibility decorator to each command:\n"
    report += "   - `@compatible_command()` for regular commands\n"
    report += "   - `@compatible_slash_command()` for slash commands\n"
    report += "   - `@compatible_group()` for command groups\n"
    report += "2. Use `respond_to_context()` instead of direct `ctx.send()` calls\n"
    report += "3. Use `normalize_context()` when you need to access context attributes\n"
    
    return report