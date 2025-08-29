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
from typing import Optional, List
from datetime import datetime

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import config, ConfigError
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
        # Validate configuration before initializing
        try:
            config.validate_config()
        except ConfigError as e:
            logger.error(f"Configuration validation failed: {e}")
            sys.exit(1)
        
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
    
    async def get_health_status(self) -> dict:
        """Get health status for monitoring."""
        status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "discord": self.is_ready(),
                "gemini_client": self.gemini_client is not None,
                "rate_limiter": self.rate_limiter is not None,
                "batch_processor": self.batch_processor is not None,
            },
            "guild_count": len(self.guilds) if hasattr(self, 'guilds') else 0,
            "user_count": len(self.users) if hasattr(self, 'users') else 0
        }
        
        # Check if all services are healthy
        if not all(status["services"].values()):
            status["status"] = "degraded"
        
        return status
    
    async def _should_use_batch(self, user_id: str, prompts: List[str]) -> bool:
        """Determine if batch processing should be used."""
        if not config.ENABLE_BATCH_PROCESSING:
            return False
        
        # Use batch for multiple prompts or if user has pending requests
        if len(prompts) > 1:
            return True
            
        # For single prompts, use batch if it would provide cost savings
        # and the user doesn't need immediate results
        return False  # Single prompts use regular API for speed
    
    async def _process_with_batch_or_regular(self, prompts: List[str], user_id: str, generation_type: str = "create") -> List[dict]:
        """Process prompts using batch or regular API based on configuration."""
        if await self._should_use_batch(user_id, prompts):
            # Use batch processing
            logger.info(f"Using batch processing for {len(prompts)} prompts")
            batch_id = str(uuid.uuid4())[:8]
            results = await self.batch_processor.process_batch(prompts, user_id, batch_id)
            
            # Convert batch results to standard format
            processed_results = []
            for prompt, image_bytes in results:
                processed_results.append({
                    'prompt': prompt,
                    'image_bytes': image_bytes,
                    'cost': config.BATCH_IMAGE_COST,  # 50% discount from config
                    'generation_type': generation_type,
                    'batch_id': batch_id
                })
            return processed_results
        else:
            # Use regular API
            processed_results = []
            for prompt in prompts:
                try:
                    image_bytes = await self.gemini_client.generate_image(prompt)
                    processed_results.append({
                        'prompt': prompt,
                        'image_bytes': image_bytes,
                        'cost': config.STANDARD_IMAGE_COST,  # Standard cost from config
                        'generation_type': generation_type,
                        'batch_id': None
                    })
                except Exception as e:
                    logger.error(f"Regular generation failed for prompt '{prompt}': {e}")
                    # Continue with other prompts
            return processed_results

    async def _init_services(self) -> None:
        """Initialize external services."""
        try:
            # Initialize Gemini client
            self.gemini_client = GeminiImageClient(config.GEMINI_API_KEY)
            
            # Initialize batch processing
            self.batch_processor = GeminiBatchProcessor(config.GEMINI_API_KEY)
            self.batch_manager = BatchManager(self.batch_processor)

            # Initialize rate limiter with configurable cleanup
            self.rate_limiter = RateLimiter(
                max_requests=config.MAX_REQUESTS_PER_HOUR,
                window_hours=1,
                cleanup_interval=config.RATE_LIMITER_CLEANUP_INTERVAL
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
            
            # Check rate limit with detailed feedback
            if not await self.rate_limiter.check_user(user_id):
                status = await self.rate_limiter.get_user_status(user_id)
                reset_time = status.get('reset_time')
                requests_used = status.get('requests_used', 0)
                
                embed = discord.Embed(
                    title="⏰ Rate Limited",
                    description=f"You've used {requests_used}/{config.MAX_REQUESTS_PER_HOUR} requests this hour.",
                    color=0xE02B2B
                )
                if reset_time:
                    minutes = int(reset_time / 60)
                    seconds = int(reset_time % 60)
                    embed.add_field(
                        name="Reset Time", 
                        value=f"⏱️ {minutes}m {seconds}s", 
                        inline=False
                    )
                embed.add_field(
                    name="💡 Tip", 
                    value="Rate limits help manage API costs and ensure fair usage for all users.", 
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return

            try:
                # Process using batch or regular API
                results = await self._process_with_batch_or_regular([prompt], user_id, "create")
                
                if not results:
                    raise Exception("No results generated")
                
                result = results[0]  # Single prompt result
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                work = ImageWork(
                    id=str(uuid.uuid4())[:8],
                    user_id=user_id,
                    prompt=result['prompt'],
                    image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                    generation_type=result['generation_type'],
                    cost=result['cost'],
                    batch_id=result['batch_id']
                )
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Send result
                file = discord.File(io.BytesIO(result['image_bytes']), filename=f"{work.id}.png")
                
                embed = discord.Embed(
                    title="🍌 Image Created!",
                    description=f"**Prompt:** {result['prompt']}",
                    color=0x00FF00
                )
                embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
                if result['batch_id']:
                    embed.add_field(name="Batch ID", value=f"`{result['batch_id']}`", inline=True)
                    embed.add_field(name="Cost Savings", value="50% off!", inline=True)
                embed.set_footer(text="Use /gallery to see all your works")
                
                await interaction.followup.send(file=file, embed=embed)
                logger.info(f"Generated image for user {user_id}: {result['prompt']} (Cost: ${result['cost']:.4f})")
                
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
            
            # Check rate limit with detailed feedback
            if not await self.rate_limiter.check_user(user_id):
                status = await self.rate_limiter.get_user_status(user_id)
                reset_time = status.get('reset_time')
                requests_used = status.get('requests_used', 0)
                
                embed = discord.Embed(
                    title="⏰ Rate Limited",
                    description=f"You've used {requests_used}/{config.MAX_REQUESTS_PER_HOUR} requests this hour.",
                    color=0xE02B2B
                )
                if reset_time:
                    minutes = int(reset_time / 60)
                    seconds = int(reset_time % 60)
                    embed.add_field(
                        name="Reset Time", 
                        value=f"⏱️ {minutes}m {seconds}s", 
                        inline=False
                    )
                embed.add_field(
                    name="💡 Tip", 
                    value="Rate limits help manage API costs and ensure fair usage for all users.", 
                    inline=False
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
            
            # Check rate limit with detailed feedback
            if not await self.rate_limiter.check_user(user_id):
                status = await self.rate_limiter.get_user_status(user_id)
                reset_time = status.get('reset_time')
                requests_used = status.get('requests_used', 0)
                
                embed = discord.Embed(
                    title="⏰ Rate Limited",
                    description=f"You've used {requests_used}/{config.MAX_REQUESTS_PER_HOUR} requests this hour.",
                    color=0xE02B2B
                )
                if reset_time:
                    minutes = int(reset_time / 60)
                    seconds = int(reset_time % 60)
                    embed.add_field(
                        name="Reset Time", 
                        value=f"⏱️ {minutes}m {seconds}s", 
                        inline=False
                    )
                embed.add_field(
                    name="💡 Tip", 
                    value="Rate limits help manage API costs and ensure fair usage for all users.", 
                    inline=False
                )
                await interaction.followup.send(embed=embed)
                return

            try:
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

        @self.tree.command(name="fuse-images", description="Fuse/combine multiple images into one using AI")
        @app_commands.describe(
            prompt="Describe how to combine/fuse multiple images",
            image1="First image to fuse",
            image2="Second image to fuse", 
            image3="Third image (optional)",
            image4="Fourth image (optional)",
            image5="Fifth image (optional)"
        )
        async def fuse_images(
            interaction: discord.Interaction, 
            prompt: str,
            image1: discord.Attachment,
            image2: discord.Attachment,
            image3: discord.Attachment = None,
            image4: discord.Attachment = None,
            image5: discord.Attachment = None
        ):
            """Fuse/combine multiple images into one using AI."""
            await interaction.response.defer()
            
            user_id = str(interaction.user.id)
            
            # Check rate limit with detailed feedback
            if not await self.rate_limiter.check_user(user_id):
                status = await self.rate_limiter.get_user_status(user_id)
                reset_time = status.get('reset_time')
                requests_used = status.get('requests_used', 0)
                
                embed = discord.Embed(
                    title="⏰ Rate Limited",
                    description=f"You've used {requests_used}/{config.MAX_REQUESTS_PER_HOUR} requests this hour.",
                    color=0xE02B2B
                )
                if reset_time:
                    minutes = int(reset_time / 60)
                    seconds = int(reset_time % 60)
                    embed.add_field(
                        name="Reset Time", 
                        value=f"⏱️ {minutes}m {seconds}s", 
                        inline=False
                    )
                embed.add_field(
                    name="💡 Tip",
                    value="Image fusion counts as 1 request regardless of image count",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
                return
            
            # Collect all provided images
            images = [image1, image2]
            if image3: images.append(image3)
            if image4: images.append(image4) 
            if image5: images.append(image5)
            
            # Validate image attachments
            for i, img in enumerate(images):
                if not img.content_type or not img.content_type.startswith('image/'):
                    embed = discord.Embed(
                        title="❌ Invalid File",
                        description=f"Image {i+1} must be an image file",
                        color=0xE02B2B
                    )
                    await interaction.followup.send(embed=embed)
                    return
                
                if img.size > config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                    embed = discord.Embed(
                        title="📁 File Too Large",
                        description=f"Image {i+1} must be under {config.MAX_IMAGE_SIZE_MB}MB",
                        color=0xE02B2B
                    )
                    await interaction.followup.send(embed=embed)
                    return
            
            try:
                # Download all images
                image_data_list = []
                for img in images:
                    image_data = await img.read()
                    image_data_list.append(image_data)
                
                # Show processing message
                embed = discord.Embed(
                    title="🔄 Fusing Images...",
                    description=f"Combining {len(images)} images with Gemini 2.5 Flash\nThis may take a few moments...",
                    color=0xFFD700
                )
                processing_msg = await interaction.followup.send(embed=embed)
                
                # Fuse images using Gemini
                result_image_data = await self.gemini_client.fuse_multiple_images(prompt, image_data_list)
                
                # Save result and create work record
                work_id = str(uuid.uuid4())[:8]
                work = ImageWork(
                    id=work_id,
                    user_id=user_id,
                    prompt=f"FUSE: {prompt}",
                    image_url="",  # Will be updated after save
                    generation_type="fuse",
                    cost=config.STANDARD_IMAGE_COST  # Same cost as regular generation
                )
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Delete processing message and send result
                await processing_msg.delete()
                
                # Create result embed
                embed = discord.Embed(
                    title="🎨 Images Fused Successfully!",
                    description=f"**Prompt:** {prompt}\n**Images combined:** {len(images)}",
                    color=0x00FF00
                )
                embed.add_field(
                    name="💰 Cost", 
                    value=f"${config.STANDARD_IMAGE_COST:.3f}", 
                    inline=True
                )
                embed.add_field(
                    name="🆔 Work ID", 
                    value=work_id, 
                    inline=True
                )
                embed.set_footer(text=f"User: {interaction.user.display_name} • BananaBot v1.2.0")
                
                # Send result with fused image
                file = discord.File(io.BytesIO(result_image_data), filename=f"fused_{work_id}.png")
                await interaction.followup.send(embed=embed, file=file)
                
            except Exception as e:
                logger.error(f"Image fusion error: {e}")
                embed = discord.Embed(
                    title="❌ Fusion Failed",
                    description=f"Failed to fuse images: {str(e)[:100]}...",
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
                title="🍌 BananaBot v1.3.0",
                description="AI Image Generation Bot with Multi-Image Fusion",
                color=0xFFD700
            )
            
            embed.add_field(
                name="🍌 Available Commands",
                value=(
                    "`/generate <prompt>` - Generate an AI image from text\n"
                    "`/generate-with-image <prompt> <image>` - Edit an attached image\n"
                    "`/generate-link <prompt> <url>` - Edit an image from URL\n"
                    "`/fuse-images <prompt> <img1> <img2> [img3-5]` - Combine multiple images\n"
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
                    "• Use `/fuse-images` to combine 2-5 images creatively\n"
                    "• All your creations are saved in your gallery"
                ),
                inline=False
            )
            
            embed.set_footer(text="BananaBot v1.3.0 • Multi-Image Fusion & AI Generation")
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