"""
Command Usage Examples

This module shows how to use the enhanced command handlers and option parsers
in a way that's compatible with py-cord 2.6.1.
"""

import discord
from utils.command_handlers import enhanced_slash_command
from utils.command_parameter_builder import (
    text_option, 
    number_option, 
    choice_option, 
    user_option, 
    channel_option, 
    add_parameter_options
)
from utils.premium_verification import premium_feature_required

class ExampleCog(discord.Cog):
    """Example cog demonstrating the enhanced slash commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @enhanced_slash_command(
        name="example",
        description="An example command showing parameter handling"
    )
    async def example_command(
        self, 
        ctx,
        text = None,
        number = 0
    ):
        """
        Example command demonstrating parameter handling.
        
        Args:
            ctx: The interaction context
            text: Text parameter to echo back
            number: Optional number parameter
        """
        await ctx.respond(f"You said: {text}, and the number is {number}")
    
    # Add the option decorators separately using our parameter builders
    add_parameter_options(example_command, {
        'text': text_option(name="text", description="Some text to echo back", required=True),
        'number': number_option(name="number", description="A number parameter", required=False)
    })
    
    @enhanced_slash_command(
        name="premium_example",
        description="Example of a premium-only command"
    )
    @premium_feature_required("priority_support")
    async def premium_example_command(
        self,
        ctx,
        feature = None
    ):
        """
        Example of a premium-gated command using the decorator.
        
        Args:
            ctx: The interaction context
            feature: The premium feature to demonstrate
        """
        await ctx.respond(f"Premium feature '{feature}' accessed successfully!")
        
    # Add the option decorator separately using our parameter builders
    add_parameter_options(premium_example_command, {
        'feature': choice_option(
            name="feature",
            description="Premium feature to demonstrate",
            choices=["analytics", "custom_reports", "priority"],
            required=True
        )
    })

    @enhanced_slash_command(
        name="complex_example",
        description="Example with multiple parameter types"
    )
    async def complex_parameter_command(
        self,
        ctx,
        text = None,
        choice = None,
        user = None,
        channel = None
    ):
        """
        Demonstrates handling of multiple parameter types.
        
        Args:
            ctx: The interaction context
            text: Text parameter
            choice: Choice from options
            user: Optional user reference
            channel: Optional channel reference
        """
        response = (
            f"Text: {text}\n"
            f"Choice: {choice}\n"
        )
        
        if user:
            response += f"User: {user.mention}\n"
        
        if channel:
            response += f"Channel: {channel.mention}\n"
        
        await ctx.respond(response)
        
    # Add the option decorators separately using our parameter builders
    add_parameter_options(complex_parameter_command, {
        'text': text_option(
            name="text",
            description="Text input",
            required=True
        ),
        'choice': choice_option(
            name="choice",
            description="Select an option",
            choices=["Option A", "Option B", "Option C"],
            required=True
        ),
        'user': user_option(
            name="user",
            description="Select a user",
            required=False
        ),
        'channel': channel_option(
            name="channel",
            description="Select a channel",
            required=False
        )
    })
        
def setup(bot):
    """Add the example cog to the bot"""
    bot.add_cog(ExampleCog(bot))