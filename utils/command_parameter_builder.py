"""
Command Parameter Building Utilities

This module provides utilities for building slash command parameters
in a way that is compatible with py-cord 2.6.1 and avoids common LSP/typing issues.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Type, cast

import discord
from utils.command_imports import get_option_class

logger = logging.getLogger(__name__)

# Get the Option class from discord
Option = get_option_class()

def build_option(
    name: str,
    description: str,
    required: bool = False,
    choices: Optional[List[str]] = None,
    option_type: Optional[Type] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    autocomplete: Optional[bool] = None
) -> Any:
    """
    Build an option object for slash commands without LSP typing issues.
    
    Args:
        name: Name of the option
        description: Description of the option
        required: Whether the option is required
        choices: List of choices for the option
        option_type: Type of the option
        min_value: Minimum value for number options
        max_value: Maximum value for number options
        autocomplete: Whether autocomplete is enabled
        
    Returns:
        Option object for use in slash commands
    """
    # Build the option kwargs
    kwargs = {
        "name": name,
        "description": description,
        "required": required
    }
    
    # Add optional parameters if provided
    if choices is not None:
        kwargs["choices"] = choices
        
    if option_type is not None:
        kwargs["type"] = option_type
        
    if min_value is not None:
        kwargs["min_value"] = min_value
        
    if max_value is not None:
        kwargs["max_value"] = max_value
        
    if autocomplete is not None:
        kwargs["autocomplete"] = autocomplete
    
    # Create and return the option
    try:
        return Option(**kwargs)
    except Exception as e:
        logger.error(f"Error creating option '{name}': {e}")
        # Return a basic option as fallback
        return Option(name=name, description=description)

def add_parameter_options(command_func: Callable, options_dict: Dict[str, Any]) -> None:
    """
    Add parameter options to a command function.
    
    Args:
        command_func: The command function to add options to
        options_dict: Dictionary mapping parameter names to Option objects
    """
    for param_name, option_obj in options_dict.items():
        try:
            setattr(command_func, param_name, option_obj)
        except Exception as e:
            logger.error(f"Error adding option '{param_name}' to command: {e}")

def text_option(name: str, description: str, required: bool = True) -> Any:
    """
    Create a text option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(name, description, required=required)

def number_option(name: str, description: str, required: bool = True,
                 min_value: Optional[Union[int, float]] = None,
                 max_value: Optional[Union[int, float]] = None) -> Any:
    """
    Create a number option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Option object
    """
    return build_option(
        name, description, required=required,
        min_value=min_value, max_value=max_value,
        option_type=int  # Use int as default type
    )

def choice_option(name: str, description: str, choices: List[str], required: bool = True) -> Any:
    """
    Create a choice option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        choices: List of choices
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(name, description, required=required, choices=choices)

def user_option(name: str, description: str, required: bool = True) -> Any:
    """
    Create a user option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(
        name, description, required=required,
        option_type=discord.Member  # Use discord.Member as the type
    )

def channel_option(name: str, description: str, required: bool = True) -> Any:
    """
    Create a channel option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(
        name, description, required=required,
        option_type=discord.TextChannel  # Use discord.TextChannel as the type
    )

def role_option(name: str, description: str, required: bool = True) -> Any:
    """
    Create a role option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(
        name, description, required=required,
        option_type=discord.Role  # Use discord.Role as the type
    )

def boolean_option(name: str, description: str, required: bool = True) -> Any:
    """
    Create a boolean option with common defaults.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option object
    """
    return build_option(
        name, description, required=required,
        option_type=bool  # Use bool as the type
    )