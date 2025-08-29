"""
BananaBot - Discord AI Image Generation Bot with Slash Commands
Public Version - Safe for GitHub
"""

import asyncio
import io
import logging
import os
import platform
import sys
import uuid
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config
from bot.services.gemini_client import GeminiImageClient
from bot.services.batch_client_v2 import GeminiBatchProcessor, BatchManager
from bot.utils.rate_limiter import RateLimiter
from bot.models import UserGallery, ImageWork, UserStats, ensure_data_directories

# Ensure .env file exists
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
    Main Discord bot class for BananaBot with slash commands.
    Public version - safe for GitHub.
    """

    def __init__(self) -> None:
        """Initialize the bot with proper configuration."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="/",  # Slash commands
            intents=intents,
            help_command=None
        )

        # Bot services - initialized in setup_hook
        self.gemini_client: Optional[GeminiImageClient] = None
        self.batch_processor: Optional[GeminiBatchProcessor] = None
        self.batch_manager: Optional[BatchManager] = None
        self.rate_limiter: Optional[RateLimiter] = None

        logger.info("BananaBot initialized with slash commands")

    async def setup_hook(self) -> None:
        """
        Async setup - called after bot is logged in but before on_ready.
        This is where we initialize services and sync commands.
        """
        logger.info("Starting bot setup...")

        # Ensure data directories exist on volume-ash-2
        ensure_data_directories()

        # Initialize services
        await self._init_services()

        # Add slash commands
        self._add_commands()

        logger.info("Bot setup completed")

    async def _init_services(self) -> None:
        """Initialize external services."""
        try:
            # Initialize Gemini client
            self.gemini_client = GeminiImageClient(config.GEMINI_API_KEY)
            
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

    def _add_commands(self) -> None:
        """Add all slash commands to the bot."""
        
        @self.tree.command(name="generate", description="Generate an AI image from text")
        @app_commands.describe(prompt="Describe the image you want to create")
        async def generate(interaction: discord.Interaction, prompt: str):
            """Generate an image from text prompt."""
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            
            # Check rate limit
            if not await self.rate_limiter.check_user(user_id):
                embed = discord.Embed(
                    title="Rate Limited",
                    description="You're making requests too quickly. Please wait a moment and try again.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)
                return

            try:
                # Generate image
                image_bytes = await self.gemini_client.generate_image(prompt)
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                work = ImageWork(
                    id=str(uuid.uuid4())[:8],
                    user_id=user_id,
                    prompt=prompt,
                    image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                    generation_type="create",
                    cost=0.039
                )
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Send result
                file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
                
                embed = discord.Embed(
                    title="🍌 Image Created!",
                    description=f"**Prompt:** {prompt}",
                    color=0x00FF00
                )
                embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
                embed.set_footer(text="Use /gallery to see all your works")
                
                await interaction.followup.send(file=file, embed=embed)
                logger.info(f"Generated image for user {user_id}: {prompt}")
                
            except Exception as e:
                logger.error(f"Image generation failed for user {user_id}: {e}")
                embed = discord.Embed(
                    title="Generation Failed",
                    description="Sorry, image generation failed. Please try again with a different prompt.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)

        @self.tree.command(name="generate-with-image", description="Edit an attached image with AI")
        @app_commands.describe(
            prompt="Describe how to modify the image",
            image="The image to edit"
        )
        async def generate_with_image(interaction: discord.Interaction, prompt: str, image: discord.Attachment):
            """Edit an attached image using AI."""
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            
            # Check rate limit
            if not await self.rate_limiter.check_user(user_id):
                embed = discord.Embed(
                    title="Rate Limited",
                    description="You're making requests too quickly. Please wait a moment and try again.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)
                return

            # Validate image
            if not image.content_type or not image.content_type.startswith('image/'):
                embed = discord.Embed(
                    title="Invalid File",
                    description="Please attach a valid image file (PNG, JPG, etc.).",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)
                return

            try:
                # Download image
                image_data = await image.read()
                
                # Edit image
                image_bytes = await self.gemini_client.edit_image(
                    prompt=prompt,
                    image_data=image_data
                )
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                work = ImageWork(
                    id=str(uuid.uuid4())[:8],
                    user_id=user_id,
                    prompt=prompt,
                    image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                    generation_type="edit",
                    cost=0.039
                )
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Send result
                file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
                
                embed = discord.Embed(
                    title="🍌 Image Edited!",
                    description=f"**Edit:** {prompt}",
                    color=0x00FF00
                )
                embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
                embed.set_footer(text="Use /gallery to see all your works")
                
                await interaction.followup.send(file=file, embed=embed)
                logger.info(f"Edited image for user {user_id}: {prompt}")
                
            except Exception as e:
                logger.error(f"Image edit failed for user {user_id}: {e}")
                embed = discord.Embed(
                    title="Edit Failed",
                    description="Sorry, image editing failed. Please try again.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)

        @self.tree.command(name="generate-link", description="Generate an image from an image URL")
        @app_commands.describe(
            prompt="Describe how to modify the image",
            image_url="URL of the image to edit"
        )
        async def generate_link(interaction: discord.Interaction, prompt: str, image_url: str):
            """Edit an image from a URL."""
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            
            # Check rate limit
            if not await self.rate_limiter.check_user(user_id):
                embed = discord.Embed(
                    title="Rate Limited",
                    description="You're making requests too quickly. Please wait a moment and try again.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)
                return

            try:
                import aiohttp
                
                # Download image from URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            raise Exception("Failed to download image")
                        image_data = await response.read()
                
                # Edit image
                image_bytes = await self.gemini_client.edit_image(
                    prompt=prompt,
                    image_data=image_data
                )
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                work = ImageWork(
                    id=str(uuid.uuid4())[:8],
                    user_id=user_id,
                    prompt=f"{prompt} (from URL)",
                    image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                    generation_type="edit",
                    cost=0.039
                )
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Send result
                file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
                
                embed = discord.Embed(
                    title="🍌 Image Edited from URL!",
                    description=f"**Edit:** {prompt}",
                    color=0x00FF00
                )
                embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
                embed.set_footer(text="Use /gallery to see all your works")
                
                await interaction.followup.send(file=file, embed=embed)
                logger.info(f"Edited image from URL for user {user_id}: {prompt}")
                
            except Exception as e:
                logger.error(f"Image edit from URL failed for user {user_id}: {e}")
                embed = discord.Embed(
                    title="Edit Failed",
                    description="Failed to process the image URL. Please check the URL is valid and accessible.",
                    color=0xE02B2B
                )
                await interaction.followup.send(embed=embed)

        @self.tree.command(name="gallery", description="View your recent image creations")
        @app_commands.describe(limit="Number of recent works to show (1-10)")
        async def gallery(interaction: discord.Interaction, limit: int = 5):
            """Display user's recent image gallery."""
            user_id = str(interaction.user.id)
            limit = min(max(limit, 1), 10)
            
            gallery = UserGallery.load(user_id)
            recent_works = gallery.get_recent_works(limit)
            
            if not recent_works:
                embed = discord.Embed(
                    title="Empty Gallery",
                    description="You haven't created any images yet! Use `/generate` to create your first one.",
                    color=0x9932CC
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title=f"🖼️ {interaction.user.display_name}'s Gallery",
                description=f"Showing your {len(recent_works)} most recent works",
                color=0x9932CC
            )
            
            for i, work in enumerate(recent_works, 1):
                created = work.created_at.strftime('%m/%d %H:%M')
                prompt_preview = work.prompt[:60] + ('...' if len(work.prompt) > 60 else '')
                
                embed.add_field(
                    name=f"{i}. {work.generation_type.title()} - `{work.id}`",
                    value=f"**Prompt:** {prompt_preview}\n**Created:** {created}",
                    inline=False
                )
            
            embed.add_field(
                name="📊 Stats",
                value=f"Total works: {gallery.total_generations}",
                inline=False
            )
            embed.set_footer(text="Use /generate to create more images")
            
            await interaction.response.send_message(embed=embed)

        @self.tree.command(name="help", description="Get help with BananaBot commands")
        async def help_command(interaction: discord.Interaction):
            """Display help information."""
            embed = discord.Embed(
                title="🍌 BananaBot Help",
                description="AI Image Generation Bot",
                color=0xFFD700
            )
            
            embed.add_field(
                name="🍌 Available Commands",
                value=(
                    "`/generate <prompt>` - Generate an AI image from text\n"
                    "`/generate-with-image <prompt> <image>` - Edit an attached image\n"
                    "`/generate-link <prompt> <url>` - Edit an image from URL\n"
                    "`/gallery [limit]` - View your image gallery\n"
                    "`/help` - Show this help message"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 Tips",
                value=(
                    "• Use `/generate` for creating new images from text\n"
                    "• Use `/generate-with-image` to modify your own images\n"
                    "• Use `/generate-link` to edit images from the web\n"
                    "• All your creations are saved in your gallery"
                ),
                inline=False
            )
            
            embed.set_footer(text="BananaBot - AI Image Generation")
            await interaction.response.send_message(embed=embed)

    async def on_ready(self) -> None:
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {platform.python_version()}")
        logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")


async def main():
    """Main entry point."""
    # Validate configuration
    config.validate_config()
    
    # Create and run bot
    async with BananaBot() as bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())