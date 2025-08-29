"""Configuration management for BananaBot."""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for BananaBot."""
    
    # Discord Configuration
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: Optional[str] = os.getenv("GUILD_ID")
    
    # Gemini API Configuration  
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.5-flash-image-preview"
    
    # Rate Limiting
    MAX_REQUESTS_PER_HOUR: int = int(os.getenv("MAX_REQUESTS_PER_HOUR", "10"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Image Processing
    MAX_IMAGE_SIZE_MB: int = 8  # Discord limit
    SUPPORTED_FORMATS: tuple = ("PNG", "JPEG", "JPG", "WEBP")
    
    # Content Safety
    ENABLE_CONTENT_FILTER: bool = os.getenv("ENABLE_CONTENT_FILTER", "true").lower() == "true"
    
    # Batch Processing
    ENABLE_BATCH_PROCESSING: bool = os.getenv("ENABLE_BATCH_PROCESSING", "false").lower() == "true"
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "10"))
    BATCH_TIMEOUT: int = int(os.getenv("BATCH_TIMEOUT", "60"))
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate that all required environment variables are set.
        
        Raises:
            ValueError: If required environment variables are missing.
        """
        missing_vars = []
        
        if not cls.DISCORD_TOKEN:
            missing_vars.append("DISCORD_TOKEN")
        
        if not cls.GEMINI_API_KEY:
            missing_vars.append("GEMINI_API_KEY")
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please check your .env file or set these environment variables."
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