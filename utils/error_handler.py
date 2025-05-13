import logging
import traceback
import discord
from discord.ext import commands
import config

logger = logging.getLogger(__name__)

async def on_command_error(ctx, error):
    """Global error handler for command exceptions"""
    
    # Get the original error if it's wrapped in a CommandInvokeError
    error = getattr(error, 'original', error)
    
    # Skip errors that are already handled locally
    if hasattr(ctx.command, 'on_error'):
        return
    
    # Skip if command has local error handler
    if ctx.cog and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
        return
    
    # Create a base embed for errors
    embed = discord.Embed(title="Error", color=config.COLORS["ERROR"])
    
    # Handle specific error types
    if isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors
        return
    
    elif isinstance(error, commands.DisabledCommand):
        embed.description = f"Command `{ctx.command}` is currently disabled."
    
    elif isinstance(error, commands.NoPrivateMessage):
        embed.description = f"Command `{ctx.command}` cannot be used in private messages."
    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed.description = f"Missing required argument: `{error.param.name}`"
        embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.name} {ctx.command.signature}`", inline=False)
    
    elif isinstance(error, commands.BadArgument):
        embed.description = f"Invalid argument: {str(error)}"
    
    elif isinstance(error, commands.ArgumentParsingError):
        embed.description = str(error)
    
    elif isinstance(error, commands.CommandOnCooldown):
        embed.description = f"This command is on cooldown. Try again in {error.retry_after:.1f}s."
    
    elif isinstance(error, commands.MissingPermissions):
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
        embed.description = f"You're missing the following permissions to run this command: {', '.join(missing)}"
    
    elif isinstance(error, commands.BotMissingPermissions):
        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in error.missing_permissions]
        embed.description = f"I'm missing the following permissions to run this command: {', '.join(missing)}"
    
    elif isinstance(error, commands.CheckFailure):
        embed.description = "You do not have permission to use this command."
    
    else:
        # For all other errors, log them and send a generic message
        logger.error(f"Command error in {ctx.command}:", exc_info=error)
        
        # More detailed error for admins, generic for regular users
        if ctx.author.id in config.ADMIN_IDS:
            embed.description = f"An error occurred: `{str(error)}`"
            error_traceback = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
            
            # Split traceback if it's too long
            if len(error_traceback) > 1000:
                error_traceback = error_traceback[:997] + "..."
            
            embed.add_field(name="Traceback", value=f"```py\n{error_traceback}\n```", inline=False)
        else:
            embed.description = "An unexpected error occurred. The bot administrators have been notified."
    
    # Send the error message
    try:
        await ctx.send(embed=embed, ephemeral=True)
    except discord.HTTPException:
        # If the embed is too large, send a simplified error message
        await ctx.send("An error occurred. Please check your input or try again later.", ephemeral=True)
