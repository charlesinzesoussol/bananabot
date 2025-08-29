"""
BananaBot - Discord AI Image Generation Bot
Implemented using proper Discord bot template structure
"""

import asyncio
import logging
import os
import platform
import random
import sys
from pathlib import Path

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context

from bot.config import config
from bot.services.gemini_client import GeminiImageClient
from bot.services.batch_client_v2 import GeminiBatchProcessor, BatchManager
from bot.utils.rate_limiter import RateLimiter
from bot.utils.error_handler import error_handler

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/.env"):
    sys.exit("'.env' not found! Please add it and try again.")

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bananabot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BananaBot(commands.Bot):
    """
    Main Discord bot class for BananaBot.
    Follows Discord.py best practices with proper template structure.
    """

    def __init__(self) -> None:
        """Initialize the bot with proper configuration."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,  # We'll create our own help command
            case_insensitive=True
        )

        # Bot services - initialized in setup_hook
        self.gemini_client: GeminiImageClient = None
        self.batch_processor: GeminiBatchProcessor = None 
        self.batch_manager: BatchManager = None
        self.rate_limiter: RateLimiter = None

        # Track initial load
        self.initial_extensions = [
            "cogs.image_generation",
            "cogs.utility"
        ]

        logger.info("BananaBot initialized")

    async def setup_hook(self) -> None:
        """
        Async setup - called after bot is logged in but before on_ready.
        This is where we initialize services and load extensions.
        """
        logger.info("Starting bot setup...")

        # Initialize services
        await self._init_services()

        # Load all cogs/extensions
        await self._load_extensions()

        # Start background tasks
        if not self.status_task.is_running():
            self.status_task.start()

        logger.info("Bot setup completed")

    async def _init_services(self) -> None:
        """Initialize external services."""
        try:
            # Initialize Gemini client
            self.gemini_client = GeminiImageClient(config.GEMINI_API_KEY)
            
            # Test connection (optional)
            health_ok = await self.gemini_client.health_check()
            if not health_ok:
                logger.warning("Gemini API health check failed")

            # Initialize batch processing
            self.batch_processor = GeminiBatchProcessor(config.GEMINI_API_KEY)
            self.batch_manager = BatchManager(self.batch_processor)

            # Initialize rate limiter
            self.rate_limiter = RateLimiter(
                max_requests=config.MAX_REQUESTS_PER_HOUR,
                window_hours=1
            )

            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise

    async def _load_extensions(self) -> None:
        """Load all bot extensions/cogs."""
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {platform.python_version()}")
        logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Log loaded commands
        total_commands = len([cmd for cmd in self.walk_commands()])
        logger.info(f"Loaded {total_commands} commands from {len(self.cogs)} cogs")

        # Clear any old slash commands by syncing empty tree
        try:
            await self.tree.sync()
            logger.info("Command tree synced (slash commands cleared)")
        except Exception as e:
            logger.warning(f"Could not sync command tree: {e}")

    async def on_message(self, message: discord.Message) -> None:
        """Process messages for commands."""
        if message.author.bot:
            return

        # Process commands
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """Called when a command completes successfully."""
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        
        if context.guild is not None:
            logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) "
                f"by {context.author} (ID: {context.author.id})"
            )
        else:
            logger.info(
                f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
            )

    async def on_command_error(self, context: Context, error) -> None:
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed, delete_after=10)
        else:
            logger.error(f"An error occurred: {error}")

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """Background task to update bot status."""
        statuses = [
            "🍌 !generate to create images",
            "🎨 AI image generation", 
            "🍌 !help for commands"
        ]
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name=random.choice(statuses)
            )
        )

    @status_task.before_loop
    async def before_status_task(self) -> None:
        """Wait until bot is ready before starting status task."""
        await self.wait_until_ready()


async def main():
    """Main entry point."""
    # Validate configuration
    config.validate_config()

    # Create and run bot
    async with BananaBot() as bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())