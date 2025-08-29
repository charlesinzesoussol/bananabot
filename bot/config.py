"""Configuration management for BananaBot."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConfigError(Exception):
    """Configuration validation error."""
    pass

class Config:
    """Configuration class for BananaBot with validation."""
    
    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: Optional[str] = os.getenv("GUILD_ID")
    
    # Gemini API Configuration  
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.5-flash-image-preview"
    
    # Rate Limiting - Production safe defaults with bounds
    MAX_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_REQUESTS_PER_HOUR", "3"))
    """Rate limit per user per hour. Production recommended: 1-50 based on API costs."""
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Image Processing
    MAX_IMAGE_SIZE_MB: int = 8  # Discord limit
    SUPPORTED_FORMATS: tuple = ("PNG", "JPEG", "JPG", "WEBP")
    
    # Content Safety
    ENABLE_CONTENT_FILTER: bool = os.getenv("ENABLE_CONTENT_FILTER", "true").lower() == "true"
    
    # Batch Processing - Production safe defaults
    ENABLE_BATCH_PROCESSING: bool = os.getenv("ENABLE_BATCH_PROCESSING", "false").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    """Batch size for bulk processing. Max recommended: 100 (Gemini API limit)."""
    BATCH_TIMEOUT: int = int(os.getenv("BATCH_TIMEOUT", "1800"))  # 30 minutes
    """Batch timeout in seconds. Gemini batch target: 24 hours, minimum: 5 minutes."""
    
    # Cost Management
    STANDARD_IMAGE_COST: float = 0.039  # $0.039 per image (Gemini 2.5 Flash)
    BATCH_IMAGE_COST: float = 0.0195   # 50% discount for batch processing
    
    # Rate Limiter Configuration
    RATE_LIMITER_CLEANUP_INTERVAL: int = int(os.getenv("RATE_LIMITER_CLEANUP_INTERVAL", "3600"))
    """Rate limiter cleanup interval in seconds. Default: 1 hour."""
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate that all required environment variables are set and values are safe.
        
        Raises:
            ConfigError: If configuration is invalid or unsafe.
        """
        missing_vars = []
        
        # Required variables
        if not cls.DISCORD_TOKEN:
            missing_vars.append("DISCORD_TOKEN")
        
        if not cls.GEMINI_API_KEY:
            missing_vars.append("GEMINI_API_KEY")
        
        if missing_vars:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please check your .env file or set these environment variables."
            )
        
        # Validate rate limiting bounds (prevent abuse)
        if not (1 <= cls.MAX_REQUESTS_PER_HOUR <= 1000):
            raise ConfigError(
                f"MAX_REQUESTS_PER_HOUR must be between 1-1000, got {cls.MAX_REQUESTS_PER_HOUR}"
            )
        
        # Validate batch processing bounds
        if not (1 <= cls.BATCH_SIZE <= 100):
            raise ConfigError(
                f"BATCH_SIZE must be between 1-100 (Gemini API limit), got {cls.BATCH_SIZE}"
            )
        
        # Validate batch timeout (minimum 5 minutes for AI generation)
        if cls.BATCH_TIMEOUT < 300:
            raise ConfigError(
                f"BATCH_TIMEOUT must be at least 300 seconds (5 minutes), got {cls.BATCH_TIMEOUT}"
            )
        
        # Validate cleanup interval
        if cls.RATE_LIMITER_CLEANUP_INTERVAL < 60:
            raise ConfigError(
                f"RATE_LIMITER_CLEANUP_INTERVAL must be at least 60 seconds, got {cls.RATE_LIMITER_CLEANUP_INTERVAL}"
            )
    
    @classmethod
    def setup_logging(cls) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('bananabot.log', mode='a')
            ]
        )
        
        # Set discord.py logging to WARNING to reduce noise
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)

# Global config instance
config = Config()