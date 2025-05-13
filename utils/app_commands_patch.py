"""
app_commands compatibility for py-cord 2.6.1

This module provides a compatibility layer for app_commands functionality,
which is implemented differently in discord.py vs py-cord 2.6.1.
"""

import inspect
import logging
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast, overload, get_type_hints

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

# Type variables for command function typing
CommandT = TypeVar('CommandT', bound=Callable[..., Any])
T = TypeVar('T')

class AppCommandsBridge:
    """
    A bridge class that mimics discord.py's app_commands module for py-cord 2.6.1
    """
    
    def __init__(self):
        """Initialize the bridge"""
        pass
        
    def command(
        self, 
        *, 
        name: Optional[str] = None, 
        description: Optional[str] = None
    ) -> Callable[[CommandT], CommandT]:
        """
        Decorator to create a slash command
        
        Args:
            name: Name of the command
            description: Description of the command
            
        Returns:
            Decorator function
        """
        def decorator(func: CommandT) -> CommandT:
            # Use py-cord's slash_command decorator underneath
            cmd = commands.slash_command(
                name=name,
                description=description or "No description provided"
            )(func)
            
            # Store the original function for reference
            setattr(cmd, "_original_function", func)
            
            return cast(CommandT, cmd)
            
        return decorator
        
    def describe(self, **kwargs) -> Callable[[CommandT], CommandT]:
        """
        Decorator to add descriptions to parameters
        
        Args:
            **kwargs: Parameter name to description mapping
            
        Returns:
            Decorator function
        """
        def decorator(func: CommandT) -> CommandT:
            # Store parameter descriptions for later use by slash command creation
            if not hasattr(func, "__parameter_descriptions__"):
                setattr(func, "__parameter_descriptions__", {})
                
            param_desc = getattr(func, "__parameter_descriptions__")
            param_desc.update(kwargs)
            
            return func
            
        return decorator
        
    def choices(self, **kwargs) -> Callable[[CommandT], CommandT]:
        """
        Decorator to add choices to parameters
        
        Args:
            **kwargs: Parameter name to choices mapping
            
        Returns:
            Decorator function
        """
        def decorator(func: CommandT) -> CommandT:
            # Store parameter choices for later use by slash command creation
            if not hasattr(func, "__parameter_choices__"):
                setattr(func, "__parameter_choices__", {})
                
            param_choices = getattr(func, "__parameter_choices__")
            
            # Process each parameter's choices
            for param_name, choices_list in kwargs.items():
                # Convert to py-cord's choice format if needed
                processed_choices = []
                
                for choice in choices_list:
                    if isinstance(choice, tuple) and len(choice) == 2:
                        # Already in (name, value) format
                        processed_choices.append(choice)
                    else:
                        # Convert single value to (str(value), value) format
                        processed_choices.append((str(choice), choice))
                        
                param_choices[param_name] = processed_choices
                
            return func
            
        return decorator
        
    def autocomplete(self, **kwargs) -> Callable[[CommandT], CommandT]:
        """
        Decorator to add autocomplete to parameters
        
        Args:
            **kwargs: Parameter name to autocomplete function mapping
            
        Returns:
            Decorator function
        """
        def decorator(func: CommandT) -> CommandT:
            # Store parameter autocomplete for later use by slash command creation
            if not hasattr(func, "__parameter_autocomplete__"):
                setattr(func, "__parameter_autocomplete__", {})
                
            param_autocomplete = getattr(func, "__parameter_autocomplete__")
            param_autocomplete.update(kwargs)
            
            return func
            
        return decorator

# Create a single instance of the bridge for easy importing
app_commands_bridge = AppCommandsBridge()

# Export the command function directly for easier importing
command = app_commands_bridge.command

# Compatibility classes for Choice
class Choice:
    """
    Compatibility class for app_commands.Choice in discord.py
    """
    
    def __init__(self, name: str, value: Any):
        """
        Initialize a choice
        
        Args:
            name: Display name of the choice
            value: Value of the choice
        """
        self.name = name
        self.value = value
        
    def __str__(self):
        return self.name
        
    # Make the Choice class look like a tuple for compatibility
    def __getitem__(self, idx):
        if idx == 0:
            return self.name
        elif idx == 1:
            return self.value
        raise IndexError("Choice index out of range")
        
    # Make Choice instances comparable
    def __eq__(self, other):
        if isinstance(other, Choice):
            return self.name == other.name and self.value == other.value
        elif isinstance(other, tuple) and len(other) == 2:
            return self.name == other[0] and self.value == other[1]
        return False