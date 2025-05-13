"""
Command Parameter Builder for Discord API Compatibility

This module provides utilities for building command parameters with proper type annotations
in a way that's compatible with both discord.py and py-cord across different versions.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast, get_type_hints

try:
    import discord
    from discord.ext import commands
    
    # Import from our local compatibility modules
    from utils.command_handlers import is_pycord_261_or_later
    
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

class CommandParameter:
    """
    Command parameter with backwards-compatible type annotations.
    
    This class is used to define command parameters in a way that's compatible
    with both discord.py and py-cord across different versions.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        type: Any = str,
        required: bool = True,
        default: Any = None,
        choices: Optional[List[Union[str, int, float]]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
    ):
        """
        Initialize a command parameter.
        
        Args:
            name: Parameter name
            description: Parameter description
            type: Parameter type (str, int, float, bool, discord.User, etc.)
            required: Whether the parameter is required
            default: Default value
            choices: Available choices for the parameter
            min_value: Minimum value for int/float parameters
            max_value: Maximum value for int/float parameters
        """
        self.name = name
        self.description = description
        self.type = type
        self.required = required
        self.default = default
        self.choices = choices
        self.min_value = min_value
        self.max_value = max_value
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the parameter to a dictionary.
        
        Returns:
            Dictionary representation of the parameter
        """
        param_dict = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "required": self.required,
        }
        
        # Add optional attributes if they're set
        if self.default is not None:
            param_dict["default"] = self.default
            
        if self.choices:
            param_dict["choices"] = self.choices
            
        if self.min_value is not None:
            param_dict["min_value"] = self.min_value
            
        if self.max_value is not None:
            param_dict["max_value"] = self.max_value
            
        return param_dict

class CommandBuilder:
    """
    Builder for creating commands with proper parameter handling.
    
    This class provides a fluent interface for building commands with parameters
    in a way that's compatible with both discord.py and py-cord across different versions.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        callback: Callable,
        guild_ids: Optional[List[int]] = None,
    ):
        """
        Initialize a command builder.
        
        Args:
            name: Command name
            description: Command description
            callback: Command callback function
            guild_ids: Optional list of guild IDs to make this a guild command
        """
        self.name = name
        self.description = description
        self.callback = callback
        self.guild_ids = guild_ids
        self.parameters: Dict[str, CommandParameter] = {}
        
    def add_parameter(self, parameter: CommandParameter) -> 'CommandBuilder':
        """
        Add a parameter to the command.
        
        Args:
            parameter: Parameter to add
            
        Returns:
            Self for method chaining
        """
        self.parameters[parameter.name] = parameter
        return self
        
    def add_string_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
        default: Optional[str] = None,
        choices: Optional[List[str]] = None,
    ) -> 'CommandBuilder':
        """
        Add a string parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            default: Default value
            choices: Available choices for the parameter
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=str,
            required=required,
            default=default,
            choices=choices,
        )
        return self.add_parameter(parameter)
        
    def add_integer_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
        default: Optional[int] = None,
        choices: Optional[List[int]] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> 'CommandBuilder':
        """
        Add an integer parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            default: Default value
            choices: Available choices for the parameter
            min_value: Minimum value
            max_value: Maximum value
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=int,
            required=required,
            default=default,
            choices=choices,
            min_value=min_value,
            max_value=max_value,
        )
        return self.add_parameter(parameter)
        
    def add_float_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
        default: Optional[float] = None,
        choices: Optional[List[float]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> 'CommandBuilder':
        """
        Add a float parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            default: Default value
            choices: Available choices for the parameter
            min_value: Minimum value
            max_value: Maximum value
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=float,
            required=required,
            default=default,
            choices=choices,
            min_value=min_value,
            max_value=max_value,
        )
        return self.add_parameter(parameter)
        
    def add_boolean_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
        default: Optional[bool] = None,
    ) -> 'CommandBuilder':
        """
        Add a boolean parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            default: Default value
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=bool,
            required=required,
            default=default,
        )
        return self.add_parameter(parameter)
        
    def add_user_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
    ) -> 'CommandBuilder':
        """
        Add a user parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=discord.User,
            required=required,
        )
        return self.add_parameter(parameter)
        
    def add_channel_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
    ) -> 'CommandBuilder':
        """
        Add a channel parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=discord.abc.GuildChannel,
            required=required,
        )
        return self.add_parameter(parameter)
        
    def add_role_parameter(
        self,
        name: str,
        description: str,
        required: bool = True,
    ) -> 'CommandBuilder':
        """
        Add a role parameter to the command.
        
        Args:
            name: Parameter name
            description: Parameter description
            required: Whether the parameter is required
            
        Returns:
            Self for method chaining
        """
        parameter = CommandParameter(
            name=name,
            description=description,
            type=discord.Role,
            required=required,
        )
        return self.add_parameter(parameter)
        
    def build(self) -> Any:
        """
        Build the command for the current Discord library version.
        
        Returns:
            Built command with parameters
        """
        # Create parameter descriptions
        descriptions = {name: param.description for name, param in self.parameters.items()}
        
        # Create parameter defaults
        defaults = {name: param.default for name, param in self.parameters.items() if param.default is not None}
        
        # Create decorator chains based on library version
        if is_pycord_261_or_later():
            # Using py-cord 2.6.1+
            try:
                # Import the enhanced slash command
                from utils.command_handlers import enhanced_slash_command
                
                # Create command with parameters
                cmd = enhanced_slash_command(
                    name=self.name,
                    description=self.description,
                )
                
                # Apply command to function
                cmd_instance = cmd(self.callback)
                
                # Add parameter descriptions
                for name, description in descriptions.items():
                    cmd_instance.add_parameter_description(name, description)
                
                return cmd_instance
            except Exception as e:
                logger.error(f"Error building command for py-cord 2.6.1+: {e}")
                raise
        else:
            # Using older py-cord or discord.py
            try:
                # Import the app commands module
                if hasattr(commands.Bot, "slash_command"):
                    # Using py-cord
                    from discord import app_commands
                    
                    # Create command with parameters
                    cmd = commands.slash_command(
                        name=self.name,
                        description=self.description,
                    )
                    
                    # Apply command to function
                    cmd_instance = cmd(self.callback)
                    
                    # Add parameter descriptions
                    describe = app_commands.describe(**descriptions)
                    cmd_instance = describe(cmd_instance)
                    
                    return cmd_instance
                else:
                    # Using discord.py
                    from discord.app_commands import command
                    
                    # Create command with parameters
                    cmd = command(
                        name=self.name,
                        description=self.description,
                    )
                    
                    # Apply command to function
                    cmd_instance = cmd(self.callback)
                    
                    return cmd_instance
            except Exception as e:
                logger.error(f"Error building command for older library: {e}")
                raise