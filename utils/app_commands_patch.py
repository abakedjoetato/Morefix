"""
app_commands_patch module for Discord bot

This module bridges compatibility between discord.py and py-cord 2.6.1 for app_commands.
It provides all the app_commands functionality as a single object that can be imported.
"""

import logging
import discord
from typing import Any, Callable, List, Optional, Union, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Create a class for Choice to be compatible across versions
class Choice:
    """Choice class compatible across discord.py and py-cord"""
    def __init__(self, name: str, value: Union[str, int, float]):
        self.name = name
        self.value = value
        
    def __repr__(self):
        return f"<Choice name={self.name!r} value={self.value!r}>"

# Create a bridge for app_commands functionality
class AppCommandsBridge:
    """Bridge for app_commands functionality between discord.py and py-cord 2.6.1"""
    
    def command(self, **kwargs):
        """Compatible command decorator"""
        # We need to handle both direct decorator and factory pattern
        def decorator(func):
            # In py-cord 2.6.1, we use the slash_command decorator
            slash_command = discord.slash_command(**kwargs)
            return slash_command(func)
        
        return decorator
    
    def describe(self, **kwargs):
        """Compatible describe decorator"""
        def decorator(func):
            # For py-cord 2.6.1
            if hasattr(discord, 'option'):
                for name, description in kwargs.items():
                    discord.option(name, description=description)(func)
            return func
        
        return decorator
    
    def choices(self, **kwargs):
        """Compatible choices decorator"""
        def decorator(func):
            # For py-cord 2.6.1
            if hasattr(discord, 'option'):
                for name, choices_list in kwargs.items():
                    if isinstance(choices_list, list):
                        options = []
                        for choice in choices_list:
                            if isinstance(choice, Choice):
                                options.append((choice.name, choice.value))
                            elif isinstance(choice, tuple) and len(choice) == 2:
                                options.append(choice)
                            else:
                                # If it's just a string/value, use it for both name and value
                                options.append((str(choice), choice))
                        discord.option(name, choices=options)(func)
            return func
        
        return decorator
    
    def autocomplete(self, **kwargs):
        """Compatible autocomplete decorator"""
        def decorator(func):
            # For py-cord 2.6.1 
            if hasattr(discord, 'option'):
                for name, autocomplete_func in kwargs.items():
                    discord.option(name, autocomplete=autocomplete_func)(func)
            return func
        
        return decorator

# Create a singleton instance
app_commands_bridge = AppCommandsBridge()