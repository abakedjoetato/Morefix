import os
import discord
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Config:
    """Configuration settings for the Discord bot"""
    
    # Bot command prefix
    PREFIX = os.environ.get("COMMAND_PREFIX", "!")
    
    # MongoDB connection URI
    MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/discordbot")
    
    # Database name to use
    DB_NAME = os.environ.get("DB_NAME", "discordbot")
    
    # Logging configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    
    # Discord embed colors
    EMBED_COLOR = discord.Color.from_rgb(59, 136, 195)  # Blue
    ERROR_COLOR = discord.Color.from_rgb(231, 76, 60)   # Red
    SUCCESS_COLOR = discord.Color.from_rgb(46, 204, 113)  # Green
    WARNING_COLOR = discord.Color.from_rgb(241, 196, 15)  # Yellow
    
    # Premium tiers
    PREMIUM_TIERS = {
        "basic": {
            "name": "Basic",
            "price": 5,
            "features": ["Faster processing", "Priority support"]
        },
        "pro": {
            "name": "Pro",
            "price": 10,
            "features": ["All Basic features", "Advanced analytics", "Custom branding"]
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 25,
            "features": ["All Pro features", "Dedicated support", "Custom integrations"]
        }
    }
    
    # API rate limits
    RATE_LIMIT_STANDARD = 5  # requests per minute
    RATE_LIMIT_PREMIUM = 20  # requests per minute
    
    # Canvas configuration
    CANVAS_WIDTH = 32
    CANVAS_HEIGHT = 32
    
    # Economy system configuration
    DAILY_CREDITS = 100
    VOTE_CREDITS = 50
    
    # Bounty system settings
    MIN_BOUNTY_AMOUNT = 100
    MAX_BOUNTY_AMOUNT = 10000
    BOUNTY_EXPIRY_DAYS = 7

# Export common constants for easier imports
EMBED_COLOR = Config.EMBED_COLOR
ERROR_COLOR = Config.ERROR_COLOR
SUCCESS_COLOR = Config.SUCCESS_COLOR
WARNING_COLOR = Config.WARNING_COLOR
PREMIUM_TIERS = Config.PREMIUM_TIERS
COMMAND_PREFIX = Config.PREFIX

# Constants for embeds
EMBED_FOOTER = "Tower of Temptation Bot • Created with ♥"
EMBED_FOOTER_ICON = "https://i.imgur.com/7Xd2lKj.png"

# CSV and Log Parser Constants
CSV_FIELDS = [
    "timestamp", "killer_name", "killer_id", "victim_name", "victim_id", 
    "weapon", "distance", "platform"
]

# Event patterns for log processing
EVENT_PATTERNS = {
    "kill": r"(?P<killer_name>.*) killed (?P<victim_name>.*) with (?P<weapon>.*) at (?P<distance>\d+) meters",
    "join": r"(?P<player_name>.*) joined the server",
    "leave": r"(?P<player_name>.*) left the server",
    "chat": r"\[(?P<channel>.*)\] (?P<player_name>.*): (?P<message>.*)"
}
