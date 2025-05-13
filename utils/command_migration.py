"""
Command Migration Helpers for Tower of Temptation PvP Statistics Bot

This module provides utilities for migrating commands:
1. Automatic command parameter conversion
2. Legacy command routing
3. Command signature validation
4. Migration documentation generation

These utilities help maintain backward compatibility for extensions.
"""
import inspect
import logging
import os
import re
import json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union, get_type_hints

# Import compatibility layer for decorator access
from utils.command_compatibility_layer import (
    normalize_context, respond_to_context, IS_PYCORD,
    get_command_signature, check_signature_compatibility
)

# Setup logger
logger = logging.getLogger(__name__)

# Command migration registry
_COMMAND_MIGRATIONS = {}
_DEPRECATED_COMMANDS = set()
_COMMAND_ALIASES = {}

def register_command_migration(old_name: str, new_name: str, transform_func: Optional[Callable] = None):
    """Register a command migration from old name to new name
    
    Args:
        old_name: Old command name
        new_name: New command name
        transform_func: Optional function to transform parameters
    """
    _COMMAND_MIGRATIONS[old_name] = {
        'new_name': new_name,
        'transform_func': transform_func
    }
    
    logger.info(f"Registered command migration from '{old_name}' to '{new_name}'")
    
    # Add to deprecated commands
    _DEPRECATED_COMMANDS.add(old_name)

def register_command_alias(command_name: str, aliases: List[str]):
    """Register aliases for a command
    
    Args:
        command_name: Command name
        aliases: List of aliases
    """
    for alias in aliases:
        _COMMAND_ALIASES[alias] = command_name
    
    logger.info(f"Registered aliases for '{command_name}': {aliases}")

def mark_as_deprecated(command_name: str, removal_version: str, alternative: Optional[str] = None):
    """Mark a command as deprecated
    
    Args:
        command_name: Command name to mark as deprecated
        removal_version: Version when this command will be removed
        alternative: Alternative command to use
    """
    _DEPRECATED_COMMANDS.add(command_name)
    
    logger.info(f"Marked command '{command_name}' as deprecated, to be removed in {removal_version}")
    if alternative:
        logger.info(f"  Alternative: {alternative}")

def get_migration_for_command(command_name: str) -> Optional[Dict[str, Any]]:
    """Get migration info for a command if it exists
    
    Args:
        command_name: Command name to check
        
    Returns:
        Migration info or None if not migrated
    """
    return _COMMAND_MIGRATIONS.get(command_name)

def is_command_deprecated(command_name: str) -> bool:
    """Check if a command is deprecated
    
    Args:
        command_name: Command name to check
        
    Returns:
        True if command is deprecated
    """
    return command_name in _DEPRECATED_COMMANDS

def get_command_alias(alias: str) -> Optional[str]:
    """Get the main command name for an alias
    
    Args:
        alias: Alias to look up
        
    Returns:
        Main command name or None if not an alias
    """
    return _COMMAND_ALIASES.get(alias)

def migrate_command_parameters(command_name: str, parameters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Migrate command parameters for compatibility
    
    Args:
        command_name: Original command name
        parameters: Original parameters
        
    Returns:
        Tuple of (new_command_name, new_parameters)
    """
    migration = get_migration_for_command(command_name)
    
    if migration:
        # Get new command name
        new_command_name = migration['new_name']
        
        # Transform parameters if necessary
        transform_func = migration.get('transform_func')
        if transform_func and callable(transform_func):
            new_parameters = transform_func(parameters)
        else:
            new_parameters = parameters
            
        return new_command_name, new_parameters
    
    # Check if it's an alias
    alias_target = get_command_alias(command_name)
    if alias_target:
        return alias_target, parameters
    
    # No migration needed
    return command_name, parameters

def parameter_type_converter(value: Any, target_type: Any) -> Any:
    """Convert a parameter value to the target type
    
    Args:
        value: Value to convert
        target_type: Type to convert to
        
    Returns:
        Converted value
    """
    if value is None:
        return None
        
    if target_type is None:
        return value
    
    # Get the type name if it's a typing object
    type_name = getattr(target_type, "__name__", str(target_type))
    
    try:
        if target_type is bool and isinstance(value, str):
            return value.lower() in ('true', 'yes', 'y', '1', 'on')
        elif target_type is int:
            return int(value)
        elif target_type is float:
            return float(value)
        elif target_type is str:
            return str(value)
        elif target_type is list and isinstance(value, str):
            return value.split(',')
        elif hasattr(target_type, "__origin__") and target_type.__origin__ is list:
            # This is a List[X] type
            if isinstance(value, str):
                items = value.split(',')
                # Try to convert items to the right type
                if hasattr(target_type, "__args__") and target_type.__args__:
                    item_type = target_type.__args__[0]
                    return [parameter_type_converter(item, item_type) for item in items]
                return items
            elif isinstance(value, list):
                return value
            else:
                return [value]
        else:
            # Try direct conversion
            return target_type(value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert value '{value}' to type '{type_name}': {e}")
        return value

def adapt_parameters_to_signature(func: Callable, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt parameters to match function signature
    
    Args:
        func: Function to adapt parameters for
        parameters: Parameters to adapt
        
    Returns:
        Adapted parameters
    """
    # Get function signature
    sig = inspect.signature(func)
    
    # Get type hints
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}
    
    # Create new parameters dict
    adapted = {}
    
    # Process each parameter in the signature
    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'ctx', 'context', 'interaction'):
            continue
            
        # Check if parameter exists in provided parameters
        if param_name in parameters:
            value = parameters[param_name]
            
            # Get expected type
            expected_type = type_hints.get(param_name, None)
            
            # Convert value if needed
            adapted[param_name] = parameter_type_converter(value, expected_type)
        elif param.default is not param.empty:
            # Use default value
            adapted[param_name] = param.default
    
    return adapted

def generate_migration_report() -> str:
    """Generate a report of all command migrations
    
    Returns:
        Markdown formatted migration report
    """
    report = "# Command Migration Report\n\n"
    
    # Add migrations
    if _COMMAND_MIGRATIONS:
        report += "## Command Migrations\n\n"
        report += "| Old Command | New Command |\n"
        report += "|------------|------------|\n"
        
        for old_name, migration in sorted(_COMMAND_MIGRATIONS.items()):
            new_name = migration['new_name']
            report += f"| {old_name} | {new_name} |\n"
    
    # Add deprecated commands
    if _DEPRECATED_COMMANDS:
        report += "\n## Deprecated Commands\n\n"
        report += "| Command |\n"
        report += "|--------|\n"
        
        for command in sorted(_DEPRECATED_COMMANDS):
            report += f"| {command} |\n"
    
    # Add command aliases
    if _COMMAND_ALIASES:
        report += "\n## Command Aliases\n\n"
        report += "| Alias | Main Command |\n"
        report += "|-------|-------------|\n"
        
        alias_by_command = {}
        for alias, command in _COMMAND_ALIASES.items():
            if command not in alias_by_command:
                alias_by_command[command] = []
            alias_by_command[command].append(alias)
        
        for command, aliases in sorted(alias_by_command.items()):
            report += f"| {', '.join(aliases)} | {command} |\n"
    
    return report

def save_migration_data(file_path: str = "migration_data.json") -> bool:
    """Save migration data to a file
    
    Args:
        file_path: File path to save to
        
    Returns:
        True if successful
    """
    data = {
        "migrations": _COMMAND_MIGRATIONS,
        "deprecated": list(_DEPRECATED_COMMANDS),
        "aliases": _COMMAND_ALIASES
    }
    
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save migration data: {e}")
        return False

def load_migration_data(file_path: str = "migration_data.json") -> bool:
    """Load migration data from a file
    
    Args:
        file_path: File path to load from
        
    Returns:
        True if successful
    """
    global _COMMAND_MIGRATIONS, _DEPRECATED_COMMANDS, _COMMAND_ALIASES
    
    if not os.path.exists(file_path):
        logger.warning(f"Migration data file not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        _COMMAND_MIGRATIONS = data.get("migrations", {})
        _DEPRECATED_COMMANDS = set(data.get("deprecated", []))
        _COMMAND_ALIASES = data.get("aliases", {})
        
        logger.info(f"Loaded migration data: {len(_COMMAND_MIGRATIONS)} migrations, "
                    f"{len(_DEPRECATED_COMMANDS)} deprecated commands, "
                    f"{len(_COMMAND_ALIASES)} aliases")
        return True
    except Exception as e:
        logger.error(f"Failed to load migration data: {e}")
        return False

# Common parameter transformations
def transform_parameters_camelcase_to_snake(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Transform camelCase parameter names to snake_case
    
    Args:
        parameters: Parameters to transform
        
    Returns:
        Transformed parameters
    """
    def camel_to_snake(name):
        # Convert camelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    return {camel_to_snake(k): v for k, v in parameters.items()}

def transform_parameters_snake_to_camelcase(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Transform snake_case parameter names to camelCase
    
    Args:
        parameters: Parameters to transform
        
    Returns:
        Transformed parameters
    """
    def snake_to_camel(name):
        # Convert snake_case to camelCase
        components = name.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    return {snake_to_camel(k): v for k, v in parameters.items()}

# Register common migrations
register_command_migration('getStats', 'get_stats', transform_parameters_camelcase_to_snake)
register_command_migration('showCanvas', 'canvas')
register_command_migration('addcolor', 'add_color')

# Register common aliases
register_command_alias('help', ['h', 'commands', 'cmds'])
register_command_alias('canvas', ['canv', 'grid'])