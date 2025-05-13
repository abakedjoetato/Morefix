"""
Compatibility module for Discord API libraries

This module provides utility functions and wrappers to maintain compatibility
between different versions of Discord API libraries (py-cord, discord.py).
"""
import discord
from discord.ext import commands

import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints

logger = logging.getLogger(__name__)

def get_parent_method_signature(cls: Type, method_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the signature of a method from the parent class.
    
    Args:
        cls: The class to inspect
        method_name: The name of the method
    
    Returns:
        Dict containing the signature details or None if not found
    """
    # Look through the MRO (Method Resolution Order) to find parent classes
    for parent in cls.__mro__[1:]:  # Skip the class itself
        if hasattr(parent, method_name):
            method = getattr(parent, method_name)
            if callable(method):
                sig = inspect.signature(method)
                type_hints = get_type_hints(method)
                
                return {
                    "signature": sig,
                    "parameters": sig.parameters,
                    "return_type": type_hints.get("return"),
                    "method": method
                }
    
    return None

def patch_method_signature(cls: Type, method_name: str) -> bool:
    """
    Update a method's signature to match its parent class.
    
    Args:
        cls: The class containing the method
        method_name: The name of the method to patch
    
    Returns:
        bool: True if patched successfully, False otherwise
    """
    if not hasattr(cls, method_name):
        logger.error(f"Class {cls.__name__} has no method named {method_name}")
        return False
    
    # Get the method we want to update
    method = getattr(cls, method_name)
    
    # Get parent method signature
    parent_sig = get_parent_method_signature(cls, method_name)
    if not parent_sig:
        logger.error(f"Could not find parent signature for {method_name}")
        return False
    
    # Create a wrapper that maintains the correct signature
    def create_wrapper(func, parent_sig):
        # Use exec to dynamically create a wrapper with the correct signature
        wrapper_code = f"def wrapper{parent_sig['signature']}:\n"
        wrapper_code += "    return func(*args, **kwargs)\n"
        
        namespace = {"func": func}
        exec(wrapper_code, namespace)
        return namespace["wrapper"]
    
    # Create and apply the wrapper
    try:
        wrapper = create_wrapper(method, parent_sig)
        setattr(cls, method_name, wrapper)
        return True
    except Exception as e:
        logger.error(f"Failed to patch method {method_name}: {e}")
        return False

def make_compatible_with_parent(cls: Type, method_names: List[str]) -> Dict[str, bool]:
    """
    Make multiple methods compatible with their parent class signatures.
    
    Args:
        cls: The class to modify
        method_names: List of method names to make compatible
    
    Returns:
        Dict mapping method names to success status
    """
    results = {}
    for method_name in method_names:
        results[method_name] = patch_method_signature(cls, method_name)
    
    return results

class SlashCommandOptionParser:
    """
    Parser utility for handling slash command options in different Discord library versions.
    """
    
    @staticmethod
    def parse_options(options):
        """
        Safely parse options from a slash command, handling both list and dict formats.
        
        Args:
            options: The options object from a slash command (list or dict-like)
            
        Returns:
            Dict mapping option names to values
        """
        result = {}
        
        # Handle list-style options (newer py-cord)
        if isinstance(options, list):
            for option in options:
                if hasattr(option, 'name') and hasattr(option, 'value'):
                    result[option.name] = option.value
                elif isinstance(option, dict) and 'name' in option and 'value' in option:
                    result[option['name']] = option['value']
                    
        # Handle dict-style options (older versions)
        elif hasattr(options, 'items') and callable(options.items):
            for name, value in options.items():
                result[name] = value
                
        # Handle dict-like objects without an items() method
        elif hasattr(options, 'get') and callable(options.get):
            # Try to extract options by common attribute names
            for key in ['options', 'values', 'parameters']:
                opts = options.get(key)
                if opts:
                    # Recursively parse these options
                    sub_results = SlashCommandOptionParser.parse_options(opts)
                    result.update(sub_results)
        
        return result

class PatternedChoice:
    """
    A Choice class that supports both attribute access and subscript access.
    
    This allows compatibility with different Discord API versions that may
    expect either obj.name or obj['name'] access patterns.
    """
    
    def __init__(self, data: Dict[str, Any]):
        """
        Initialize with a dictionary of data.
        
        Args:
            data: The underlying data
        """
        self._data = data
        
        # Copy keys as attributes for attribute access
        for key, value in data.items():
            setattr(self, key, value)
    
    def __getitem__(self, key: str) -> Any:
        """
        Support dictionary-style access: obj['name']
        """
        return self._data[key]
    
    def __contains__(self, key: str) -> bool:
        """
        Support 'in' operator: 'name' in obj
        """
        return key in self._data
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Dictionary-compatible get method.
        
        Args:
            key: The key to retrieve
            default: The default value if key is not found
            
        Returns:
            The value or default
        """
        return self._data.get(key, default)
    
    def items(self):
        """
        Dictionary-compatible items method.
        
        Returns:
            items view of the underlying dictionary
        """
        return self._data.items()
    
    def keys(self):
        """
        Dictionary-compatible keys method.
        
        Returns:
            keys view of the underlying dictionary
        """
        return self._data.keys()
    
    def values(self):
        """
        Dictionary-compatible values method.
        
        Returns:
            values view of the underlying dictionary
        """
        return self._data.values()

def create_command_tree(bot_instance):
    """
    Create a command tree that's compatible with the current version of discord.py/py-cord.
    
    This function abstracts away differences between discord.py and py-cord
    command tree implementations.
    
    Args:
        bot_instance: The bot instance to create a command tree for
        
    Returns:
        An appropriate CommandTree instance or equivalent
    """
    logger.info("Creating command tree for bot instance")
    
    # Determine library version and approach
    logger.info(f"Discord library version: {discord.__version__}")
    
    # For py-cord 2.6.1+, we just need to return the bot instance
    # since it directly handles commands without a separate tree
    if hasattr(discord, 'application_command') or hasattr(discord, 'slash_command'):
        logger.info("Using py-cord application command system")
        # In py-cord, the bot itself manages commands directly
        return bot_instance
    
    # For discord.py compatibility (should not reach here with py-cord)
    try:
        # Try to import app_commands - this is for discord.py only
        import importlib
        try:
            app_commands_module = importlib.import_module('discord.app_commands')
            logger.info("Using discord.py app_commands module")
            return app_commands_module.CommandTree(bot_instance)
        except (ImportError, ModuleNotFoundError):
            logger.debug("discord.app_commands module not found")
    except Exception as e:
        logger.error(f"Failed to import command tree: {e}")
    
    # Last resort: return the bot instance itself
    logger.warning("Using bot instance directly as command tree fallback")
    return bot_instance

def safely_parse_options(options):
    """
    Safely parse command options, handling both list and dict-like objects for compatibility.
    
    This helper function can work with both:
    - List-style options from newer py-cord (2.6.1+)
    - Dictionary-style options from older py-cord/discord.py
    
    Args:
        options: The options object (list or dict-like)
        
    Returns:
        Dict mapping option names to values
    """
    result = {}
    
    # Handle list-style options (py-cord 2.6.1+)
    if isinstance(options, list):
        for option in options:
            # Extract name and value using attribute access if possible
            if hasattr(option, 'name') and hasattr(option, 'value'):
                result[option.name] = option.value
            # Fallback to dictionary access if needed
            elif isinstance(option, dict) and 'name' in option and 'value' in option:
                result[option['name']] = option['value']
    
    # Handle dict-style options (older versions)
    elif hasattr(options, 'items') and callable(options.items):
        try:
            for name, value in options.items():
                result[name] = value
        except (TypeError, AttributeError) as e:
            # Log the error and try a different approach
            logger.debug(f"Error using items(): {e}")
            
            # Try dictionary-style access as fallback
            if hasattr(options, 'keys') and callable(options.keys):
                for key in options.keys():
                    try:
                        result[key] = options[key]
                    except Exception:
                        pass
    
    # Handle other types of objects by attempting attribute extraction
    else:
        # Try common attribute names that might contain options
        for key in ['options', 'values', 'parameters']:
            if hasattr(options, key):
                try:
                    value = getattr(options, key)
                    # Recursively parse if we got another container
                    if isinstance(value, (list, dict)) or hasattr(value, 'items'):
                        sub_results = safely_parse_options(value)
                        result.update(sub_results)
                except Exception:
                    pass
    
    return result