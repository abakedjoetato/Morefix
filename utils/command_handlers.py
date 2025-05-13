"""
Command Handlers for Discord API Compatibility

This module provides enhanced command classes and functions to handle
compatibility issues between different versions of discord.py and py-cord,
especially for slash commands and application commands.
"""

import logging
import inspect
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast, get_type_hints

try:
    import discord
    from discord.ext import commands
    
    # Check if we're using py-cord by looking for slash_command attribute
    USING_PYCORD = hasattr(commands.Bot, "slash_command")
    
    # Check if we're using py-cord 2.6.1+ with newer imports
    if USING_PYCORD:
        try:
            # Try importing app_commands directly (newer style)
            import discord.app_commands as app_commands
            USING_PYCORD_261_PLUS = True
        except ImportError:
            # Fall back to the old style if needed
            from discord import app_commands
            USING_PYCORD_261_PLUS = False
            
        # Get the SlashCommand class from the appropriate place
        if USING_PYCORD_261_PLUS:
            from discord.app_commands import SlashCommand
        else:
            from discord.commands import SlashCommand
    else:
        # discord.py style
        from discord.app_commands import Command as SlashCommand
        USING_PYCORD_261_PLUS = False
        
except ImportError as e:
    # Provide better error messages for missing dependencies
    logging.error(f"Failed to import Discord libraries: {e}")
    raise ImportError(
        "Failed to import Discord libraries. Please install discord.py or py-cord:\n"
        "For py-cord: pip install py-cord>=2.0.0\n"
        "For discord.py: pip install discord.py>=2.0.0"
    ) from e

# Setup logger
logger = logging.getLogger(__name__)

# Type variables for return typing
T = TypeVar('T')
CommandT = TypeVar('CommandT')

class EnhancedSlashCommand(SlashCommand):
    """
    Enhanced SlashCommand with compatibility fixes for different py-cord versions.
    
    This class overrides the _parse_options method to handle both list-style options
    (used in newer py-cord versions) and dict-style options (used in older versions).
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parameter_descriptions = {}
        
    def _parse_options(self, params: Dict[str, Any]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse command options with compatibility for different parameter styles.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            Either a dict (older style) or list (newer style) of option parameters
        """
        # If we're using py-cord 2.6.1+, we need to handle the options differently
        if USING_PYCORD_261_PLUS:
            try:
                # Newer py-cord expects a list of options
                options = []
                
                # Extract the parameters
                for name, param in params.items():
                    if name == "self" or name == "ctx":
                        continue
                        
                    option = self._extract_option_params(name, param)
                    options.append(option)
                    
                return options
            except Exception as e:
                logger.error(f"Error parsing options in newer py-cord style: {e}")
                # Fall back to super's implementation
                return super()._parse_options(params)  # type: ignore
        else:
            # Older py-cord or discord.py expects a dict of options
            try:
                options = {}
                
                # Extract the parameters
                for name, param in params.items():
                    if name == "self" or name == "ctx":
                        continue
                        
                    option = self._extract_option_params(name, param)
                    options[name] = option
                    
                return options
            except Exception as e:
                logger.error(f"Error parsing options in older py-cord style: {e}")
                # Fall back to super's implementation
                return super()._parse_options(params)  # type: ignore
                
    def _extract_option_params(self, name: str, param: Any) -> Dict[str, Any]:
        """
        Extract option parameters from a parameter.
        
        Args:
            name: Parameter name
            param: Parameter object
            
        Returns:
            Dict of option parameters
        """
        option = {
            "name": name,
            "description": self._parameter_descriptions.get(name, "No description provided"),
            "required": True,
        }
        
        # Set default if available
        if param.default is not inspect.Parameter.empty:
            option["required"] = False
            option["default"] = param.default
            
        # Set type if available
        if param.annotation is not inspect.Parameter.empty:
            option["type"] = param.annotation
            
        return option
        
    def add_parameter_description(self, name: str, description: str) -> None:
        """
        Add a description for a parameter.
        
        Args:
            name: Parameter name
            description: Parameter description
        """
        self._parameter_descriptions[name] = description

# Parameter option builders
def text_option(name: str, description: str, required: bool = True, default: str = None) -> Dict[str, Any]:
    """
    Create a text option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": str,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def number_option(name: str, description: str, required: bool = True, default: float = None) -> Dict[str, Any]:
    """
    Create a number option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": float,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def integer_option(name: str, description: str, required: bool = True, default: int = None) -> Dict[str, Any]:
    """
    Create an integer option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": int,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def boolean_option(name: str, description: str, required: bool = True, default: bool = None) -> Dict[str, Any]:
    """
    Create a boolean option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": bool,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def user_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a user option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.User,
    }

def channel_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a channel option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.abc.GuildChannel,
    }

def role_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a role option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.Role,
    }

def enhanced_slash_command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> Callable[[T], EnhancedSlashCommand]:
    """
    Decorator to create an enhanced slash command with compatibility fixes.
    
    Args:
        name: Command name
        description: Command description
        **kwargs: Additional arguments to pass to the command
        
    Returns:
        Command decorator function
    """
    def decorator(func: T) -> EnhancedSlashCommand:
        """
        Decorator to create an enhanced slash command with compatibility fixes.
        
        Args:
            func: Function to wrap
            
        Returns:
            Enhanced slash command
        """
        # Get the command name from the function name if not provided
        cmd_name = name or func.__name__
        cmd_description = description or func.__doc__ or "No description provided"
        
        # Create the command
        command = EnhancedSlashCommand(
            func,
            name=cmd_name,
            description=cmd_description,
            **kwargs
        )
        
        return command
    
    return decorator

def add_parameter_options(command: EnhancedSlashCommand, options: Dict[str, Dict[str, Any]]) -> None:
    """
    Add parameter options to a command.
    
    Args:
        command: Command to add options to
        options: Dictionary of parameter name to option parameters
    """
    # Add parameter descriptions to the command
    for name, option in options.items():
        command.add_parameter_description(name, option.get("description", "No description provided"))
        
def is_pycord_261_or_later() -> bool:
    """
    Check if we're using py-cord 2.6.1 or later.
    
    Returns:
        True if using py-cord 2.6.1 or later, False otherwise
    """
    return USING_PYCORD and USING_PYCORD_261_PLUS