"""
Discord Mocks for Tower of Temptation PvP Statistics Bot

This module provides mock Discord objects for testing:
1. Mock interactions for slash commands
2. Mock guilds, channels, messages
3. Mock users with permissions
4. Mock application context

These mocks allow for isolated testing of command functionality
without requiring an actual Discord connection.
"""
from typing import Dict, List, Any, Optional, Union, Callable, AsyncCallable
from unittest.mock import MagicMock, AsyncMock
import asyncio
import datetime
import uuid
import json
import sys
import re

# Mock the discord module if it's not available
if 'discord' not in sys.modules:
    sys.modules['discord'] = MagicMock()
    sys.modules['discord.ext'] = MagicMock()
    sys.modules['discord.ext.commands'] = MagicMock()
    sys.modules['discord.app_commands'] = MagicMock()

# Now import discord
import discord
from discord.ext import commands
import discord.app_commands

# Mock Permissions
class MockPermissions:
    """Mock Discord permissions"""
    
    def __init__(self, permissions=None):
        """Initialize with specific permissions
        
        Args:
            permissions: Dictionary of permission name to boolean
        """
        self._permissions = permissions or {}
        
        # Default permissions
        self._defaults = {
            "manage_guild": False,
            "administrator": False,
            "manage_messages": False,
            "manage_channels": False,
            "manage_roles": False,
            "ban_members": False,
            "kick_members": False,
        }
    
    def __getattr__(self, name):
        """Get a permission value
        
        Args:
            name: Permission name
            
        Returns:
            Boolean permission value
        """
        if name in self._permissions:
            return self._permissions[name]
        return self._defaults.get(name, False)

# Mock User
class MockUser:
    """Mock Discord user"""
    
    def __init__(self, 
                 id=None, 
                 name="Test User", 
                 discriminator="0000",
                 bot=False,
                 avatar_url=None,
                 permissions=None):
        """Initialize a mock user
        
        Args:
            id: User ID (default: random)
            name: Username
            discriminator: User discriminator
            bot: Whether this is a bot account
            avatar_url: URL to the user's avatar
            permissions: User's permissions
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.name = name
        self.discriminator = discriminator
        self.bot = bot
        self.avatar_url = avatar_url
        self.display_name = name
        self.mention = f"<@{self.id}>"
        self.created_at = datetime.datetime.now() - datetime.timedelta(days=30)
        self._roles = []
    
    def __str__(self):
        return f"{self.name}#{self.discriminator}"
    
    @property
    def roles(self):
        """Get user roles
        
        Returns:
            List of mock roles
        """
        return self._roles
    
    def add_role(self, role):
        """Add a role to the user
        
        Args:
            role: Role to add
        """
        if role not in self._roles:
            self._roles.append(role)
    
    def remove_role(self, role):
        """Remove a role from the user
        
        Args:
            role: Role to remove
        """
        if role in self._roles:
            self._roles.remove(role)
    
    @property
    def guild_permissions(self):
        """Get the user's guild permissions
        
        Returns:
            MockPermissions object
        """
        # Combine permissions from all roles
        all_permissions = {}
        for role in self._roles:
            for perm_name, perm_value in role.permissions._permissions.items():
                if perm_value:  # True permissions override False
                    all_permissions[perm_name] = True
        
        return MockPermissions(all_permissions)

# Mock Role
class MockRole:
    """Mock Discord role"""
    
    def __init__(self, 
                 id=None,
                 name="Test Role",
                 permissions=None,
                 position=0,
                 color=0):
        """Initialize a mock role
        
        Args:
            id: Role ID (default: random)
            name: Role name
            permissions: Role permissions
            position: Role position in hierarchy 
            color: Role color
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.name = name
        self.position = position
        self.color = color
        self.permissions = MockPermissions(permissions)
        self.mention = f"<@&{self.id}>"
    
    def __str__(self):
        return self.name

# Mock Channel
class MockChannel:
    """Mock Discord channel"""
    
    def __init__(self,
                 id=None,
                 name="test-channel",
                 type=0,  # 0 = text
                 guild=None,
                 category=None,
                 position=0,
                 topic=None):
        """Initialize a mock channel
        
        Args:
            id: Channel ID (default: random)
            name: Channel name
            type: Channel type (0=text, 2=voice, etc.)
            guild: Parent guild
            category: Parent category
            position: Channel position
            topic: Channel topic
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.name = name
        self.type = type
        self.guild = guild
        self.category = category
        self.position = position
        self.topic = topic
        self.mention = f"<#{self.id}>"
        self.created_at = datetime.datetime.now() - datetime.timedelta(days=14)
        
        # Create async mocks for channel methods
        self.send = AsyncMock(return_value=MockMessage(channel=self, guild=self.guild))
        self.history = MagicMock()
        self.history.return_value.flatten = AsyncMock(return_value=[])
    
    def __str__(self):
        return self.name

# Mock Guild (Server)
class MockGuild:
    """Mock Discord guild (server)"""
    
    def __init__(self,
                 id=None,
                 name="Test Server",
                 owner=None,
                 description=None,
                 region=None,
                 member_count=10):
        """Initialize a mock guild
        
        Args:
            id: Guild ID (default: random)
            name: Guild name
            owner: Guild owner (MockUser)
            description: Guild description
            region: Guild region
            member_count: Number of members
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.name = name
        self.description = description
        self.region = region or "us-east"
        self.member_count = member_count
        self.created_at = datetime.datetime.now() - datetime.timedelta(days=60)
        
        # Create default owner if none provided
        self.owner = owner or MockUser(name="Server Owner")
        
        # Create collections
        self._members = {}
        self._channels = {}
        self._roles = {}
        
        # Add default admin role
        admin_role = MockRole(name="Admin", permissions={"administrator": True}, position=10)
        self.add_role(admin_role)
        
        # Add default everyone role
        everyone_role = MockRole(name="@everyone", id=self.id, position=0)
        self.add_role(everyone_role)
        
        # Add owner as member with admin role
        self.add_member(self.owner)
        self.owner.add_role(admin_role)
        
        # Create fetch methods
        self.fetch_member = AsyncMock()
        self.fetch_channel = AsyncMock()
    
    def add_member(self, member):
        """Add a member to the guild
        
        Args:
            member: MockUser to add
        """
        self._members[member.id] = member
    
    def remove_member(self, member):
        """Remove a member from the guild
        
        Args:
            member: MockUser to remove
        """
        if member.id in self._members:
            del self._members[member.id]
    
    def add_channel(self, channel):
        """Add a channel to the guild
        
        Args:
            channel: MockChannel to add
        """
        channel.guild = self
        self._channels[channel.id] = channel
    
    def add_role(self, role):
        """Add a role to the guild
        
        Args:
            role: MockRole to add
        """
        self._roles[role.id] = role
    
    @property
    def members(self):
        """Get guild members
        
        Returns:
            List of members
        """
        return list(self._members.values())
    
    @property
    def channels(self):
        """Get guild channels
        
        Returns:
            List of channels
        """
        return list(self._channels.values())
    
    @property
    def roles(self):
        """Get guild roles
        
        Returns:
            List of roles
        """
        return list(self._roles.values())
    
    @property
    def default_role(self):
        """Get the default @everyone role
        
        Returns:
            MockRole for @everyone
        """
        return self._roles.get(self.id)
    
    def get_member(self, member_id):
        """Get a member by ID
        
        Args:
            member_id: ID of the member to get
            
        Returns:
            MockUser or None
        """
        return self._members.get(member_id)
    
    def get_channel(self, channel_id):
        """Get a channel by ID
        
        Args:
            channel_id: ID of the channel to get
            
        Returns:
            MockChannel or None
        """
        return self._channels.get(channel_id)
    
    def get_role(self, role_id):
        """Get a role by ID
        
        Args:
            role_id: ID of the role to get
            
        Returns:
            MockRole or None
        """
        return self._roles.get(role_id)

# Mock Message
class MockMessage:
    """Mock Discord message"""
    
    def __init__(self,
                 id=None,
                 content="Test message",
                 author=None,
                 channel=None,
                 guild=None,
                 attachments=None,
                 embeds=None,
                 referenced_message=None):
        """Initialize a mock message
        
        Args:
            id: Message ID (default: random)
            content: Message content
            author: Message author (MockUser)
            channel: Message channel
            guild: Message guild
            attachments: Message attachments
            embeds: Message embeds
            referenced_message: Reply reference
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.content = content
        self.author = author or MockUser()
        self.channel = channel
        self.guild = guild
        self.attachments = attachments or []
        self.embeds = embeds or []
        self.referenced_message = referenced_message
        self.created_at = datetime.datetime.now()
        self.edited_at = None
        self.reactions = []
        self.mention_everyone = "@everyone" in content
        self.mentions = self._extract_mentions(content)
        self.role_mentions = self._extract_role_mentions(content)
        self.channel_mentions = self._extract_channel_mentions(content)
        
        # Create async methods
        self.edit = AsyncMock(return_value=self)
        self.delete = AsyncMock()
        self.add_reaction = AsyncMock()
        self.remove_reaction = AsyncMock()
        self.pin = AsyncMock()
        self.unpin = AsyncMock()
        self.reply = AsyncMock(return_value=MockMessage(
            content="Reply to message",
            author=self.author,
            channel=self.channel,
            guild=self.guild,
            referenced_message=self
        ))
    
    def _extract_mentions(self, content):
        """Extract user mentions from content
        
        Args:
            content: Message content
            
        Returns:
            List of MockUser objects
        """
        mentions = []
        for mention in re.findall(r'<@!?(\d+)>', content):
            mentions.append(MockUser(id=int(mention)))
        return mentions
    
    def _extract_role_mentions(self, content):
        """Extract role mentions from content
        
        Args:
            content: Message content
            
        Returns:
            List of MockRole objects
        """
        role_mentions = []
        for mention in re.findall(r'<@&(\d+)>', content):
            role_mentions.append(MockRole(id=int(mention)))
        return role_mentions
    
    def _extract_channel_mentions(self, content):
        """Extract channel mentions from content
        
        Args:
            content: Message content
            
        Returns:
            List of MockChannel objects
        """
        channel_mentions = []
        for mention in re.findall(r'<#(\d+)>', content):
            channel_mentions.append(MockChannel(id=int(mention)))
        return channel_mentions

# Mock Embed
class MockEmbed:
    """Mock Discord embed"""
    
    def __init__(self,
                 title=None,
                 description=None,
                 url=None,
                 timestamp=None,
                 color=None):
        """Initialize a mock embed
        
        Args:
            title: Embed title
            description: Embed description
            url: Embed URL
            timestamp: Embed timestamp
            color: Embed color
        """
        self.title = title
        self.description = description
        self.url = url
        self.timestamp = timestamp or datetime.datetime.now()
        self.color = color
        self.fields = []
        self.footer = None
        self.image = None
        self.thumbnail = None
        self.author = None
    
    def add_field(self, name, value, inline=False):
        """Add a field to the embed
        
        Args:
            name: Field name
            value: Field value
            inline: Whether the field is inline
            
        Returns:
            Self for chaining
        """
        self.fields.append({
            "name": name,
            "value": value,
            "inline": inline
        })
        return self
    
    def set_footer(self, text=None, icon_url=None):
        """Set the embed footer
        
        Args:
            text: Footer text
            icon_url: Footer icon URL
            
        Returns:
            Self for chaining
        """
        self.footer = {
            "text": text,
            "icon_url": icon_url
        }
        return self
    
    def set_image(self, url):
        """Set the embed image
        
        Args:
            url: Image URL
            
        Returns:
            Self for chaining
        """
        self.image = {"url": url}
        return self
    
    def set_thumbnail(self, url):
        """Set the embed thumbnail
        
        Args:
            url: Thumbnail URL
            
        Returns:
            Self for chaining
        """
        self.thumbnail = {"url": url}
        return self
    
    def set_author(self, name=None, url=None, icon_url=None):
        """Set the embed author
        
        Args:
            name: Author name
            url: Author URL
            icon_url: Author icon URL
            
        Returns:
            Self for chaining
        """
        self.author = {
            "name": name,
            "url": url,
            "icon_url": icon_url
        }
        return self
    
    def to_dict(self):
        """Convert embed to dictionary
        
        Returns:
            Dictionary representation of embed
        """
        result = {}
        if self.title:
            result["title"] = self.title
        if self.description:
            result["description"] = self.description
        if self.url:
            result["url"] = self.url
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        if self.color:
            result["color"] = self.color
        if self.fields:
            result["fields"] = self.fields
        if self.footer:
            result["footer"] = self.footer
        if self.image:
            result["image"] = self.image
        if self.thumbnail:
            result["thumbnail"] = self.thumbnail
        if self.author:
            result["author"] = self.author
        return result

# Mock Interaction Types
class MockInteractionType:
    """Mock Discord interaction types"""
    ping = 1
    application_command = 2
    component = 3
    autocomplete = 4
    modal_submit = 5

# Mock Interaction
class MockInteraction:
    """Mock Discord interaction"""
    
    def __init__(self,
                 id=None,
                 type=None,
                 application_id=None,
                 user=None,
                 guild=None,
                 channel=None,
                 data=None,
                 command_name=None,
                 command_id=None,
                 options=None):
        """Initialize a mock interaction
        
        Args:
            id: Interaction ID (default: random)
            type: Interaction type (default: application_command)
            application_id: Bot application ID
            user: User who triggered the interaction
            guild: Guild where the interaction was triggered
            channel: Channel where the interaction was triggered
            data: Raw interaction data
            command_name: Name of the invoked command
            command_id: ID of the invoked command
            options: Command options
        """
        self.id = id or int(uuid.uuid4().int % 2**32)
        self.type = type or MockInteractionType.application_command
        self.application_id = application_id or int(uuid.uuid4().int % 2**32)
        self.user = user or MockUser()
        self.guild = guild
        self.channel = channel or (
            MockChannel(guild=guild) if guild else MockChannel()
        )
        self.created_at = datetime.datetime.now()
        
        # Build data if not provided
        if data is None:
            if command_name:
                data = {
                    "id": command_id or int(uuid.uuid4().int % 2**32),
                    "name": command_name,
                    "type": 1,  # CHAT_INPUT
                    "options": []
                }
                
                # Add options if provided
                if options:
                    data["options"] = options
        
        self.data = data or {}
        
        # Mock response methods
        self.response = MagicMock()
        self.response.send_message = AsyncMock()
        self.response.edit_message = AsyncMock()
        self.response.defer = AsyncMock()
        self.response.is_done = MagicMock(return_value=False)
        
        # Mock followup
        self.followup = MagicMock()
        self.followup.send = AsyncMock(
            return_value=MockMessage(
                content="Followup message",
                author=MockUser(id=application_id, bot=True),
                channel=self.channel,
                guild=self.guild
            )
        )
        
        # Add direct response methods for py-cord
        self.respond = AsyncMock(return_value=self.response)
        self.response.defer = AsyncMock()
        self.send = self.respond
        self.defer = self.response.defer
        self.edit_original_response = AsyncMock()
        self.original_response = AsyncMock(
            return_value=MockMessage(
                content="Original response",
                author=MockUser(id=application_id, bot=True),
                channel=self.channel,
                guild=self.guild
            )
        )
        
        # Add ApplicationCommandInteraction attributes
        self.command = MagicMock()
        self.command.name = command_name if command_name else "mock_command"
        self.command_name = command_name if command_name else "mock_command"
        self.command_id = command_id or int(uuid.uuid4().int % 2**32)
        self._options = options or []
    
    @property
    def options(self):
        """Get interaction options
        
        Returns:
            List of option dictionaries
        """
        if "options" in self.data:
            return self.data["options"]
        return self._options
    
    def get_option(self, name):
        """Get an option by name
        
        Args:
            name: Option name
            
        Returns:
            Option value or None
        """
        for option in self.options:
            if option["name"] == name:
                return option.get("value")
        return None

# Mock ApplicationContext (for py-cord)
class MockApplicationContext:
    """Mock Discord application context"""
    
    def __init__(self, interaction=None, **kwargs):
        """Initialize a mock application context
        
        Args:
            interaction: Underlying interaction (or will create one)
            **kwargs: Additional arguments to pass to MockInteraction
        """
        self.interaction = interaction or MockInteraction(**kwargs)
        self.bot = kwargs.get("bot", MagicMock())
        self.command = self.interaction.command
        self.command_name = self.interaction.command_name
        self.command_id = self.interaction.command_id
        self.guild = self.interaction.guild
        self.channel = self.interaction.channel
        self.user = self.interaction.user
        self.author = self.interaction.user  # Alias for user
        
        # Add response methods (delegated to interaction)
        self.respond = self.interaction.respond
        self.defer = self.interaction.defer
        self.send = self.interaction.send
        self.followup = self.interaction.followup
        self.edit = self.interaction.edit_original_response
    
    def get_option(self, name):
        """Get an option by name
        
        Args:
            name: Option name
            
        Returns:
            Option value or None
        """
        return self.interaction.get_option(name)

# Mock Context (for traditional commands)
class MockContext:
    """Mock Discord command context"""
    
    def __init__(self,
                 message=None,
                 author=None,
                 guild=None,
                 channel=None,
                 bot=None,
                 prefix="!",
                 command=None,
                 command_name=None):
        """Initialize a mock context
        
        Args:
            message: Message that triggered the command
            author: Command author
            guild: Guild where the command was triggered
            channel: Channel where the command was triggered
            bot: Bot instance
            prefix: Command prefix
            command: Command object
            command_name: Command name
        """
        self.author = author or MockUser()
        self.guild = guild
        self.channel = channel or (
            MockChannel(guild=guild) if guild else MockChannel()
        )
        self.bot = bot or MagicMock()
        
        # Create message if not provided
        if message is None:
            self.message = MockMessage(
                content=f"{prefix}{command_name or 'mock_command'}",
                author=self.author,
                channel=self.channel,
                guild=self.guild
            )
        else:
            self.message = message
        
        # Set up command info
        self.command = command or MagicMock()
        if command_name:
            self.command.name = command_name
        self.invoked_with = command_name or "mock_command"
        self.prefix = prefix
        self.command_failed = False
        self.subcommand_passed = None
        
        # Add response methods
        self.send = AsyncMock(
            return_value=MockMessage(
                content="Response message",
                author=MockUser(bot=True),
                channel=self.channel,
                guild=self.guild
            )
        )
        self.reply = AsyncMock(
            return_value=MockMessage(
                content="Reply message",
                author=MockUser(bot=True),
                channel=self.channel,
                guild=self.guild,
                referenced_message=self.message
            )
        )
    
    async def typing(self):
        """Simulate typing indicator
        
        This is an async context manager
        """
        return AsyncTypingContextManager()

# Helper for typing context manager
class AsyncTypingContextManager:
    """Async context manager for typing"""
    
    async def __aenter__(self):
        return None
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

# Factory functions
def create_mock_user(**kwargs):
    """Create a mock user
    
    Args:
        **kwargs: Arguments to pass to MockUser
        
    Returns:
        MockUser instance
    """
    return MockUser(**kwargs)

def create_mock_guild(**kwargs):
    """Create a mock guild
    
    Args:
        **kwargs: Arguments to pass to MockGuild
        
    Returns:
        MockGuild instance
    """
    return MockGuild(**kwargs)

def create_mock_interaction(**kwargs):
    """Create a mock interaction
    
    Args:
        **kwargs: Arguments to pass to MockInteraction
        
    Returns:
        MockInteraction instance
    """
    return MockInteraction(**kwargs)

def create_mock_context(**kwargs):
    """Create a mock context
    
    Args:
        **kwargs: Arguments to pass to MockContext
        
    Returns:
        MockContext instance
    """
    return MockContext(**kwargs)

def create_mock_application_context(**kwargs):
    """Create a mock application context
    
    Args:
        **kwargs: Arguments to pass to MockApplicationContext
        
    Returns:
        MockApplicationContext instance
    """
    return MockApplicationContext(**kwargs)