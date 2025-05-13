"""
Command Handlers for py-cord 2.6.1 Compatibility

This module provides enhanced command decorators and handlers that work
across different versions of py-cord and discord.py.
"""

import logging
import traceback
import functools
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Type, cast, overload

import discord
from discord.ext import commands

from utils.command_imports import (
    is_compatible_with_pycord_261,
    get_slash_command_class,
    get_option_class,
    IS_PYCORD,
    PYCORD_261,
    HAS_APP_COMMANDS
)
from utils.interaction_handlers import (
    safely_respond_to_interaction, 
    get_interaction_user
)

logger = logging.getLogger(__name__)

# Type variables for decorator typing
CommandT = TypeVar('CommandT', bound=Callable)
FuncT = TypeVar('FuncT', bound=Callable)
T = TypeVar('T')
P = TypeVar('P')

async def defer_interaction(interaction_or_ctx: Union[discord.Interaction, commands.Context], ephemeral: bool = False) -> bool:
    """
    Defer an interaction with py-cord 2.6.1 compatibility
    
    Args:
        interaction_or_ctx: The interaction or context to defer
        ephemeral: Whether the response should be ephemeral
        
    Returns:
        bool: True if the interaction was deferred, False otherwise
    """
    try:
        # Handle different types of interactions/contexts
        if isinstance(interaction_or_ctx, discord.Interaction):
            # Handle Interaction objects
            if is_compatible_with_pycord_261():
                # py-cord 2.6.1 uses interaction.response.defer
                if hasattr(interaction_or_ctx, 'response') and hasattr(interaction_or_ctx.response, 'defer'):
                    # Check if the interaction is already responded to
                    if hasattr(interaction_or_ctx.response, 'is_done') and callable(interaction_or_ctx.response.is_done):
                        if not interaction_or_ctx.response.is_done():
                            await interaction_or_ctx.response.defer(ephemeral=ephemeral)
                            return True
                        else:
                            logger.debug("Interaction already responded to, skipping defer")
                            return False
                    else:
                        # No is_done method, try deferring anyway
                        try:
                            await interaction_or_ctx.response.defer(ephemeral=ephemeral)
                            return True
                        except Exception as e:
                            logger.debug(f"Error deferring interaction: {e}")
                            return False
                else:
                    logger.warning("Cannot find response.defer on interaction")
                    return False
            else:
                # Other libraries might use defer directly
                if hasattr(interaction_or_ctx, 'defer') and callable(interaction_or_ctx.defer):
                    await interaction_or_ctx.defer(ephemeral=ephemeral)
                    return True
                else:
                    logger.warning("Cannot find defer method on interaction")
                    return False
        elif isinstance(interaction_or_ctx, commands.Context):
            # Handle Context objects
            if hasattr(interaction_or_ctx, 'defer') and callable(interaction_or_ctx.defer):
                await interaction_or_ctx.defer()
                return True
            elif hasattr(interaction_or_ctx, 'typing') and callable(interaction_or_ctx.typing):
                # Use typing as a fallback for regular commands
                async with interaction_or_ctx.typing():
                    pass
                return True
            else:
                logger.warning("Cannot find defer or typing method on context")
                return False
        else:
            logger.warning(f"Unknown interaction/context type: {type(interaction_or_ctx)}")
            return False
    except Exception as e:
        logger.error(f"Error deferring interaction: {e}")
        logger.error(traceback.format_exc())
        return False

def enhanced_slash_command(
    **kwargs
) -> Callable[[CommandT], CommandT]:
    """
    Enhanced slash command decorator with py-cord 2.6.1 compatibility
    
    This decorator uses the appropriate slash command implementation based on
    the detected Discord library version.
    
    Args:
        **kwargs: Parameters to pass to the command decorator
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        if is_compatible_with_pycord_261():
            # py-cord 2.6.1 approach
            # Import locally to avoid circular imports
            try:
                from discord.commands import slash_command
                logger.debug(f"Using py-cord 2.6.1 slash_command for {func.__name__}")
                
                # Apply the slash_command decorator with our kwargs
                return slash_command(**kwargs)(func)
            except (ImportError, AttributeError) as e:
                logger.error(f"Error using py-cord 2.6.1 slash_command: {e}")
                logger.error(traceback.format_exc())
                
                # Fallback to the standard commands
                return commands.command(**kwargs)(func)
        elif IS_PYCORD:
            # Regular py-cord approach
            try:
                from discord.ext.commands import slash_command
                logger.debug(f"Using regular py-cord slash_command for {func.__name__}")
                
                # Apply the slash_command decorator with our kwargs
                return slash_command(**kwargs)(func)
            except (ImportError, AttributeError) as e:
                logger.error(f"Error using regular py-cord slash_command: {e}")
                logger.error(traceback.format_exc())
                
                # Fallback to the standard commands
                return commands.command(**kwargs)(func)
        elif HAS_APP_COMMANDS:
            # discord.py approach with app_commands
            try:
                logger.debug(f"Using discord.py app_commands for {func.__name__}")
                
                # Note: discord.py app_commands integration needs to be handled differently
                # This needs to be registered with the bot's command tree
                return func
            except Exception as e:
                logger.error(f"Error using discord.py app_commands: {e}")
                logger.error(traceback.format_exc())
                
                # Fallback to the standard commands
                return commands.command(**kwargs)(func)
        else:
            # Fallback to standard command
            logger.debug(f"Using standard command for {func.__name__}")
            return commands.command(**kwargs)(func)
    
    return decorator

def option(**kwargs) -> Callable[[FuncT], FuncT]:
    """
    Option decorator with py-cord 2.6.1 compatibility
    
    Decorates a parameter of a slash command with options.
    
    Args:
        **kwargs: Parameters for the option
        
    Returns:
        Parameter decorator function
    """
    def decorator(func: FuncT) -> FuncT:
        if is_compatible_with_pycord_261():
            # py-cord 2.6.1 approach
            try:
                from discord.commands import Option
                
                # Store the parameter options in the function's __discord_options__ dict
                if not hasattr(func, "__discord_options__"):
                    func.__discord_options__ = {}
                
                # Get the parameter name from the name kwarg or infer from next parameter
                param_name = kwargs.get("name")
                if not param_name:
                    # Try to infer the parameter name
                    sig = inspect.signature(func)
                    params = list(sig.parameters.values())
                    
                    # Find the first parameter without an option (after self/ctx)
                    for param in params[1:]:  # Skip self/ctx
                        if param.name not in getattr(func, "__discord_options__", {}):
                            param_name = param.name
                            break
                
                if param_name:
                    func.__discord_options__[param_name] = Option(**kwargs)
                
                return func
            except (ImportError, AttributeError) as e:
                logger.error(f"Error using py-cord 2.6.1 Option: {e}")
                logger.error(traceback.format_exc())
                return func
        elif IS_PYCORD:
            # Regular py-cord approach
            try:
                from discord.commands import Option
                
                # Similar to py-cord 2.6.1
                if not hasattr(func, "__discord_options__"):
                    func.__discord_options__ = {}
                
                param_name = kwargs.get("name")
                if not param_name:
                    sig = inspect.signature(func)
                    params = list(sig.parameters.values())
                    
                    for param in params[1:]:
                        if param.name not in getattr(func, "__discord_options__", {}):
                            param_name = param.name
                            break
                
                if param_name:
                    func.__discord_options__[param_name] = Option(**kwargs)
                
                return func
            except (ImportError, AttributeError) as e:
                logger.error(f"Error using regular py-cord Option: {e}")
                logger.error(traceback.format_exc())
                return func
        elif HAS_APP_COMMANDS:
            # discord.py app_commands approach
            try:
                import discord.app_commands
                
                # No direct equivalent, but we can store the info for later
                if not hasattr(func, "__app_commands_options__"):
                    func.__app_commands_options__ = {}
                
                param_name = kwargs.get("name")
                if not param_name:
                    sig = inspect.signature(func)
                    params = list(sig.parameters.values())
                    
                    for param in params[1:]:
                        if param.name not in getattr(func, "__app_commands_options__", {}):
                            param_name = param.name
                            break
                
                if param_name:
                    func.__app_commands_options__[param_name] = kwargs
                
                return func
            except (ImportError, AttributeError) as e:
                logger.error(f"Error using discord.py app_commands options: {e}")
                logger.error(traceback.format_exc())
                return func
        else:
            # No-op for other library versions
            return func
    
    return decorator

def add_parameter_options(func: Callable, options_dict: Dict[str, Any]) -> Callable:
    """
    Add parameter options to a command function
    
    Args:
        func: The command function
        options_dict: Dictionary mapping parameter names to option objects
        
    Returns:
        The decorated function
    """
    try:
        # Store the options in the function
        if is_compatible_with_pycord_261() or IS_PYCORD:
            # py-cord approach
            if not hasattr(func, "__discord_options__"):
                func.__discord_options__ = {}
            
            func.__discord_options__.update(options_dict)
        elif HAS_APP_COMMANDS:
            # discord.py app_commands approach
            if not hasattr(func, "__app_commands_options__"):
                func.__app_commands_options__ = {}
            
            func.__app_commands_options__.update(options_dict)
    except Exception as e:
        logger.error(f"Error adding parameter options: {e}")
        logger.error(traceback.format_exc())
    
    return func

def command_handler(error_logging: bool = True, premium_check: bool = False):
    """
    Decorator for command handlers with py-cord 2.6.1 compatibility
    
    This decorator handles interaction/context differences across library versions
    and adds error handling and logging.
    
    Args:
        error_logging: Whether to log errors
        premium_check: Whether to check for premium status
        
    Returns:
        Command handler decorator
    """
    def decorator(func: CommandT) -> CommandT:
        @functools.wraps(func)
        async def wrapper(self: Any, interaction_or_ctx: Any, *args: Any, **kwargs: Any) -> Any:
            # Handle different interaction types based on library version
            try:
                # Determine if we're dealing with an interaction or context
                is_interaction = isinstance(interaction_or_ctx, discord.Interaction)
                
                if is_interaction:
                    # For interactions, handle library differences
                    if is_compatible_with_pycord_261():
                        # py-cord 2.6.1 uses interaction.response
                        pass  # No special handling needed
                    else:
                        # Other libraries might have different behavior
                        pass
                
                # Add user detection with compatibility
                user = await get_interaction_user(interaction_or_ctx)
                
                # Add context to kwargs for the handler to use
                if 'user' not in kwargs:
                    kwargs['user'] = user
                
                # Call the handler function
                result = await func(self, interaction_or_ctx, *args, **kwargs)
                return result
            except Exception as e:
                if error_logging:
                    logger.error(f"Error in command handler {func.__name__}: {e}")
                    logger.error(traceback.format_exc())
                
                # Try to respond with an error message
                try:
                    if is_interaction:
                        await safely_respond_to_interaction(
                            interaction_or_ctx,
                            content=f"An error occurred: {str(e)}",
                            ephemeral=True
                        )
                    else:
                        if hasattr(interaction_or_ctx, 'reply') and callable(interaction_or_ctx.reply):
                            await interaction_or_ctx.reply(f"An error occurred: {str(e)}")
                except Exception as response_error:
                    logger.error(f"Error sending error response: {response_error}")
                
                # Re-raise the exception for the global error handler
                raise
        
        return cast(CommandT, wrapper)
    
    return decorator

def premium_feature_required(feature_name: Optional[str] = None):
    """
    Decorator to mark a command as requiring premium status
    
    Args:
        feature_name: Optional name of the specific premium feature required
        
    Returns:
        Command decorator function
    """
    def decorator(func: CommandT) -> CommandT:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # First arg should be the interaction or context
            if not args:
                logger.error("No interaction/context provided to premium-gated command")
                return
            
            interaction_or_ctx = args[0]
            
            try:
                # Get the user
                user = await get_interaction_user(interaction_or_ctx)
                
                if not user:
                    logger.error("Could not determine user for premium check")
                    # Respond with error
                    if isinstance(interaction_or_ctx, discord.Interaction):
                        await safely_respond_to_interaction(
                            interaction_or_ctx,
                            content="Could not verify your premium status. Please try again later.",
                            ephemeral=True
                        )
                    return
                
                # Check premium status
                # This is a placeholder - implement your actual premium check here
                has_premium = True  # getattr(user, "premium", False)
                
                if not has_premium:
                    # Not premium - respond with an error
                    feature_text = f" to use {feature_name}" if feature_name else ""
                    
                    if isinstance(interaction_or_ctx, discord.Interaction):
                        await safely_respond_to_interaction(
                            interaction_or_ctx,
                            content=f"You need a premium subscription{feature_text}. " +
                                   "Type `/premium` to learn more.",
                            ephemeral=True
                        )
                    elif hasattr(interaction_or_ctx, 'reply') and callable(interaction_or_ctx.reply):
                        await interaction_or_ctx.reply(
                            f"You need a premium subscription{feature_text}. " +
                            "Type `/premium` to learn more.",
                            ephemeral=True
                        )
                    
                    return
                
                # User has premium - proceed with the command
                return await func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in premium check for {func.__name__}: {e}")
                logger.error(traceback.format_exc())
                
                # Try to respond with an error
                try:
                    if isinstance(interaction_or_ctx, discord.Interaction):
                        await safely_respond_to_interaction(
                            interaction_or_ctx,
                            content="An error occurred checking your premium status. Please try again later.",
                            ephemeral=True
                        )
                    elif hasattr(interaction_or_ctx, 'reply') and callable(interaction_or_ctx.reply):
                        await interaction_or_ctx.reply(
                            "An error occurred checking your premium status. Please try again later.",
                            ephemeral=True
                        )
                except Exception as response_error:
                    logger.error(f"Error sending premium error response: {response_error}")
                
                # Re-raise the exception for global error handler
                raise
        
        # Mark the command as premium-only for inspection
        wrapper.__premium_required__ = True
        wrapper.__premium_feature__ = feature_name
        
        return cast(CommandT, wrapper)
    
    return decorator