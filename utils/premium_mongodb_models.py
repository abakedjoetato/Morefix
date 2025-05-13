"""
MongoDB models for premium subscriptions and activation codes.
"""

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, TypeVar, Type, cast

from utils.safe_mongodb import SafeDocument

logger = logging.getLogger(__name__)

class PremiumSubscription(SafeDocument):
    """Premium subscription model for guilds"""
    
    collection_name = "premium_subscriptions"
    
    def __init__(self, 
                 guild_id: str, 
                 tier: int, 
                 activated_at: datetime, 
                 expires_at: Optional[datetime] = None,
                 activated_by: Optional[str] = None, 
                 _id: Optional[str] = None,
                 **kwargs):
        """Initialize a premium subscription
        
        Args:
            guild_id: Discord guild ID
            tier: Premium tier level
            activated_at: When the subscription was activated
            expires_at: When the subscription expires (None for never)
            activated_by: Discord user ID who activated the subscription
            _id: MongoDB document ID
        """
        super().__init__(_id=_id)
        self.guild_id = str(guild_id)
        self.tier = int(tier)
        self.activated_at = activated_at
        self.expires_at = expires_at
        self.activated_by = activated_by if activated_by else None
        
        # Add any additional kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @property
    def is_active(self) -> bool:
        """Check if the subscription is active
        
        Returns:
            bool: True if subscription is active, False otherwise
        """
        if self.expires_at is None:
            # No expiration date means it's permanently active
            return True
            
        return self.expires_at > datetime.utcnow()
    
    @classmethod
    async def get_by_guild_id(cls, guild_id: str) -> Optional['PremiumSubscription']:
        """Get a premium subscription by guild ID
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Optional[PremiumSubscription]: The subscription or None if not found
        """
        guild_id = str(guild_id)  # Ensure it's a string
        return await cls.find_one({"guild_id": guild_id})
    
    async def upgrade(self, new_tier: int, duration_days: int) -> bool:
        """Upgrade an existing subscription
        
        Args:
            new_tier: The new tier level
            duration_days: How many days to add to the current expiration
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Only upgrade tier if new tier is higher
        if new_tier > self.tier:
            self.tier = new_tier
            
        # Extend expiration if applicable
        if duration_days > 0:
            if self.expires_at is None:
                # Create an expiration date from now
                self.expires_at = datetime.utcnow() + timedelta(days=duration_days)
            else:
                # Extend from current expiration date
                self.expires_at = self.expires_at + timedelta(days=duration_days)
                
        # Save changes
        return await self.save()
    
    async def cancel(self) -> bool:
        """Cancel a subscription by setting expiration to now
        
        Returns:
            bool: True if successful, False otherwise
        """
        self.expires_at = datetime.utcnow()
        return await self.save()
        
class ActivationCode(SafeDocument):
    """Activation code model for premium subscriptions"""
    
    collection_name = "activation_codes"
    
    def __init__(self,
                code: str,
                tier: int,
                duration_days: int,
                created_at: datetime = None,
                used: bool = False,
                used_by: Optional[str] = None,
                used_at: Optional[datetime] = None,
                created_by: Optional[str] = None,
                _id: Optional[str] = None,
                **kwargs):
        """Initialize an activation code
        
        Args:
            code: Unique activation code
            tier: Premium tier level
            duration_days: Duration in days
            created_at: When the code was created
            used: Whether the code has been used
            used_by: Guild ID that used the code
            used_at: When the code was used
            created_by: Discord user ID who created the code
            _id: MongoDB document ID
        """
        super().__init__(_id=_id)
        self.code = code
        self.tier = int(tier)
        self.duration_days = int(duration_days)
        self.created_at = created_at or datetime.utcnow()
        self.used = bool(used)
        self.used_by = str(used_by) if used_by else None
        self.used_at = used_at
        self.created_by = str(created_by) if created_by else None
        
        # Add any additional kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
            
    @classmethod
    async def get_by_code(cls, code: str) -> Optional['ActivationCode']:
        """Get an activation code by its code
        
        Args:
            code: The activation code to find
            
        Returns:
            Optional[ActivationCode]: The activation code or None if not found
        """
        return await cls.find_one({"code": code})
    
    async def mark_as_used(self, guild_id: Union[str, int]) -> bool:
        """Mark this activation code as used
        
        Args:
            guild_id: Discord guild ID that used the code
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.used:
            logger.warning(f"Activation code {self.code} already used by {self.used_by}")
            return False
            
        self.used = True
        self.used_by = str(guild_id)
        self.used_at = datetime.utcnow()
        
        return await self.save()
    
    @classmethod
    async def generate_code(cls, tier: int, duration_days: int, created_by: Optional[str] = None) -> Optional['ActivationCode']:
        """Generate a new activation code
        
        Args:
            tier: Premium tier level
            duration_days: Duration in days
            created_by: Discord user ID who created the code
            
        Returns:
            Optional[ActivationCode]: The new activation code or None if failed
        """
        # Generate a random code (16 characters, alphanumeric)
        alphabet = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Insert hyphens for readability
        code = f"{code[:4]}-{code[4:8]}-{code[8:12]}-{code[12:]}"
        
        # Create the activation code
        activation_code = cls(
            code=code,
            tier=tier,
            duration_days=duration_days,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        # Save to database
        success = await activation_code.save()
        if success:
            return activation_code
        return None