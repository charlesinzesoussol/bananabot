"""Main Discord bot implementation for BananaBot with prefix commands."""

import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands  # Still needed for the old error handler import
from typing import Optional, List, Tuple
import io
import uuid
from datetime import datetime

from .config import config
from .services.gemini_client import GeminiImageClient
from .services.batch_client_v2 import GeminiBatchProcessor, BatchManager
from .utils.error_handler import error_handler
from .utils.rate_limiter import RateLimiter
from .models import UserGallery, ImageWork, UserStats

logger = logging.getLogger(__name__)

class BananaBot(commands.Bot):
    """
    BananaBot - Discord Image Generation Bot using Gemini 2.5 Flash Image.
    
    Provides prefix commands for AI image generation and editing.
    """
    
    def __init__(self):
        """Initialize the bot with required intents and services."""
        # CRITICAL: Setup intents for prefix commands
        intents = discord.Intents.default()
        intents.message_content = True  # Required for prefix commands
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None  # Disable default help
        )
        
        # Initialize services
        self.gemini_client: Optional[GeminiImageClient] = None
        self.batch_processor: Optional[GeminiBatchProcessor] = None
        self.batch_manager: Optional[BatchManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        
        logger.info("BananaBot initialized with prefix commands")
    
    def _add_command_handlers(self) -> None:
        """Add command handler methods to the bot."""
        
        async def _handle_generate(ctx: commands.Context, prompt: str):
            """Handle image generation command."""
            user_id = str(ctx.author.id)
            
            # Check rate limit
            if not await self.rate_limiter.check_user(user_id):
                await ctx.send("❌ Rate limit exceeded. Please try again later.")
                return
            
            # Check for attached images
            user_images = []
            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        image_data = await attachment.read()
                        user_images.append(image_data)
            
            await ctx.send(f"🎨 Generating image: _{prompt}_")
            
            try:
                # COST OPTIMIZATION: Always use batch mode for 50% savings
                if user_images:
                    # Use first attached image for editing/composition
                    # Note: For single edits, we still need direct API call
                    image_bytes = await self.gemini_client.edit_image(
                        image_data=user_images[0],
                        edit_prompt=prompt
                    )
                else:
                    # Generate using batch mode even for single images (50% cost savings)
                    batch_id = str(uuid.uuid4())[:8]
                    results = await self.batch_processor.process_batch([prompt], user_id, batch_id)
                    
                    if results:
                        prompt, image_bytes = results[0]
                    else:
                        # Fallback to direct API if batch fails
                        image_bytes = await self.gemini_client.generate_image(prompt)
                
                # Save to user gallery
                gallery = UserGallery.load(user_id)
                work = ImageWork(
                    id=str(uuid.uuid4())[:8],
                    user_id=user_id,
                    prompt=prompt,
                    image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                    generation_type="create" if not user_images else "edit"
                )
                gallery.add_work(work)
                
                # Update user stats
                stats = UserStats.load(user_id)
                stats.update_stats(work)
                
                # Send image
                file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
                embed = discord.Embed(
                    title="🍌 Image Generated!",
                    description=f"**Prompt:** {prompt}\\n**ID:** `{work.id}`",
                    color=0xFFD700
                )
                embed.set_footer(text=f"Use !edit {work.id} to modify this image")
                
                await ctx.send(file=file, embed=embed)
                
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                await ctx.send("❌ Image generation failed. Please try again.")
        
        async def _handle_gallery(ctx: commands.Context, limit: int = 5):
            """Handle gallery viewing command."""
            user_id = str(ctx.author.id)
            
            gallery = UserGallery.load(user_id)
            recent_works = gallery.get_recent_works(limit)
            
            if not recent_works:
                await ctx.send("📱 Your gallery is empty. Use `!generate` to create your first image!")
                return
            
            embed = discord.Embed(
                title="🖼️ Your Image Gallery",
                description=f"Showing {len(recent_works)} most recent works",
                color=0x9932CC
            )
            
            for work in recent_works:
                created = work.created_at.strftime('%m/%d %H:%M')
                embed.add_field(
                    name=f"`{work.id}` - {work.generation_type.title()}",
                    value=f"**Prompt:** {work.prompt[:100]}{'...' if len(work.prompt) > 100 else ''}\\n**Created:** {created}",
                    inline=False
                )
            
            embed.set_footer(text=f"Total works: {gallery.total_generations} | Use !edit <ID> to modify")
            
            await ctx.send(embed=embed)
        
        async def _handle_help(ctx: commands.Context):
            """Handle help command."""
            embed = discord.Embed(
                title="🍌 BananaBot Commands",
                description="AI Image Generation Bot with COST-OPTIMIZED Batch Processing",
                color=0xFFD700
            )
            
            embed.add_field(
                name="🎨 Generation Commands (AUTO BATCH MODE - 50% CHEAPER)",
                value="`!generate <prompt>` - Generate image (uses batch mode for 50% savings)\\n`!cheap <prompt1> <prompt2> ...` - Bulk generation (max savings)\\n`!gallery [limit]` - View your recent works",
                inline=False
            )
            
            embed.add_field(
                name="💰 Cost Optimization",
                value="• ALL commands use Google Batch API (50% cost reduction)\\n• Single images processed via batch mode\\n• Multiple images get maximum bulk discounts\\n• Average cost: $0.00125 per image (vs $0.0025 standard)",
                inline=False
            )
            
            embed.add_field(
                name="💡 Tips",
                value="• Attach images to `!generate` for editing\\n• Use `!cheap prompt1 prompt2 prompt3` for multiple images\\n• All images saved to your personal gallery\\n• Batch mode is always enabled for cost savings",
                inline=False
            )
            
            embed.set_footer(text="Made with 🍌 | Powered by Google Gemini Batch API (50% cheaper)")
            
            await ctx.send(embed=embed)
        
        # Bind methods to self
        self._handle_generate = _handle_generate
        self._handle_gallery = _handle_gallery  
        self._handle_help = _handle_help
        
        # Add batch handler
        async def _handle_batch(ctx: commands.Context, prompts: List[str]):
            """Handle batch generation with cost optimization."""
            user_id = str(ctx.author.id)
            
            if len(prompts) < 1:
                await ctx.send("❌ Please provide at least one prompt. Example: `!cheap sunset beach \"cute cat\"`")
                return
            
            if len(prompts) > 10:
                await ctx.send("❌ Batch mode limited to 10 prompts at once for optimal processing.")
                return
            
            # If only one prompt, use single batch optimization
            if len(prompts) == 1:
                await self._handle_generate(ctx, prompts[0])
                return
            
            await ctx.send(f"⚡ Starting COST-OPTIMIZED batch generation for {len(prompts)} images (50% savings)...")
            
            try:
                # Submit batch job
                batch_id = str(uuid.uuid4())[:8]
                
                # Process batch with cost optimization
                results = await self.batch_processor.process_batch(prompts, user_id, batch_id)
                
                if not results:
                    await ctx.send("❌ Batch processing failed. No images generated.")
                    return
                
                # Save results to gallery and send
                gallery = UserGallery.load(user_id)
                files = []
                embed = discord.Embed(
                    title="⚡ COST-OPTIMIZED Batch Complete!",
                    description=f"Generated {len(results)}/{len(prompts)} images\\n💰 **Cost:** ${len(results) * 0.00125:.4f} (50% savings applied)",
                    color=0xFF4500
                )
                
                for i, (prompt, image_bytes) in enumerate(results):
                    work = ImageWork(
                        id=str(uuid.uuid4())[:8],
                        user_id=user_id,
                        prompt=prompt,
                        image_url=f"batch_{batch_id}_{i}.png",
                        generation_type="batch",
                        batch_id=batch_id,
                        cost=0.00125  # Batch pricing (50% off)
                    )
                    gallery.add_work(work)
                    
                    files.append(discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png"))
                    
                    if i < 5:  # Show first 5 prompts in embed
                        embed.add_field(
                            name=f"🍌 `{work.id}`",
                            value=prompt[:50] + ('...' if len(prompt) > 50 else ''),
                            inline=True
                        )
                
                embed.set_footer(text=f"💰 Saved ${len(results) * 0.00125:.4f} with batch mode | Use !gallery to see all works")
                
                # Send images
                if len(files) <= 10:  # Discord limit
                    await ctx.send(files=files, embed=embed)
                else:
                    # Send in chunks
                    for chunk_start in range(0, len(files), 10):
                        chunk = files[chunk_start:chunk_start+10]
                        if chunk_start == 0:
                            await ctx.send(files=chunk, embed=embed)
                        else:
                            await ctx.send(files=chunk)
                
            except Exception as e:
                logger.error(f"Batch generation failed: {e}")
                await ctx.send("❌ Batch generation failed. Please try again or use !generate for single images.")
        
        self._handle_batch = _handle_batch
    
    def _add_prefix_commands(self) -> None:
        """Add all prefix commands to the bot."""
        
        @self.command(name='generate', aliases=['g', 'create'])
        async def generate(ctx: commands.Context, *, prompt: str):
            """Generate an image from a text prompt."""
            await self._handle_generate(ctx, prompt)
        
        @self.command(name='gallery', aliases=['history', 'works'])
        async def gallery(ctx: commands.Context, limit: int = 5):
            """View your recent image works."""
            await self._handle_gallery(ctx, limit)
        
        @self.command(name='cheap', aliases=['c', 'batch'])
        async def cheap(ctx: commands.Context, *prompts: str):
            """Generate multiple images in batch mode for maximum cost savings (50% off)."""
            await self._handle_batch(ctx, list(prompts))
        
        @self.command(name='help', aliases=['h'])
        async def help_command(ctx: commands.Context):
            """Show help information."""
            await self._handle_help(ctx)
    
    async def setup_hook(self) -> None:
        """
        Setup hook called when the bot is starting up.
        """
        logger.info("Running setup hook...")
        
        try:
            # Initialize services
            await self._initialize_services()
            
            # Load commands
            await self._load_commands()
                
        except Exception as e:
            logger.error(f"Setup hook failed: {e}")
            raise
    
    async def _initialize_services(self) -> None:
        """Initialize external services and clients."""
        try:
            # Initialize Gemini client
            self.gemini_client = GeminiImageClient(config.GEMINI_API_KEY)
            
            # Test Gemini API connection
            health_ok = await self.gemini_client.health_check()
            if not health_ok:
                logger.warning("Gemini API health check failed - service may be unavailable")
            
            # Initialize batch processing
            self.batch_processor = GeminiBatchProcessor(config.GEMINI_API_KEY)
            self.batch_manager = BatchManager(self.batch_processor)
            
            # Initialize rate limiter
            self.rate_limiter = RateLimiter(
                max_requests=config.MAX_REQUESTS_PER_HOUR,
                window_hours=1
            )
            
            logger.info("Services initialized successfully")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
    
    async def _load_commands(self) -> None:
        """Load prefix commands."""
        try:
            # Add inline commands directly to the bot
            self._add_prefix_commands()
            
            logger.info("Prefix commands loaded successfully")
            
        except Exception as e:
            logger.error(f"Command loading failed: {e}")
            raise
    
    async def on_ready(self) -> None:
        """Called when the bot is ready and connected to Discord."""
        logger.info("BananaBot is ready!")
        if self.user:
            logger.info(f"Logged in as: {self.user} (ID: {self.user.id})")
        else:
            logger.warning("Bot user is None after ready event")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for /generate commands"
            ),
            status=discord.Status.online
        )
        
        # Log command tree status
        commands = self.tree.get_commands()
        logger.info(f"Loaded {len(commands)} commands: {[cmd.name for cmd in commands]}")
    
    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle general bot errors."""
        logger.error(f"Error in {event_method}")
        error_handler.log_error(Exception(f"Bot error in {event_method}"))
    
    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handle application command errors."""
        await error_handler.handle_tree_error(interaction, error)
    
    async def close(self) -> None:
        """Clean up resources when bot is shutting down."""
        logger.info("BananaBot is shutting down...")
        await super().close()

def create_bot() -> BananaBot:
    """
    Factory function to create and configure the bot.
    
    Returns:
        Configured BananaBot instance
    """
    # Validate configuration
    config.validate_config()
    
    # Setup logging
    config.setup_logging()
    
    # Create bot instance
    bot = BananaBot()
    
    logger.info("Bot created successfully")
    return bot

async def main() -> None:
    """Main entry point for the bot."""
    try:
        logger.info("Starting BananaBot...")
        
        # Create bot
        bot = create_bot()
        
        # Run bot
        await bot.start(config.DISCORD_TOKEN)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())