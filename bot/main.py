"""Main Discord bot implementation for BananaBot with prefix commands."""

import asyncio
import logging
import discord
from discord.ext import commands
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
            
            await ctx.send(f"🎨 Creating your image: _{prompt}_")
            
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
                    title="🍌 Here's your image!",
                    description=f"**Prompt:** {prompt}\\n**ID:** `{work.id}`",
                    color=0xFFD700
                )
                embed.set_footer(text=f"Use !gallery to see all your creations")
                
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
                title="🖼️ Your Gallery",
                description=f"Here are your {len(recent_works)} most recent creations",
                color=0x9932CC
            )
            
            for work in recent_works:
                created = work.created_at.strftime('%m/%d %H:%M')
                embed.add_field(
                    name=f"`{work.id}` - {work.generation_type.title()}",
                    value=f"**Prompt:** {work.prompt[:100]}{'...' if len(work.prompt) > 100 else ''}\\n**Created:** {created}",
                    inline=False
                )
            
            embed.set_footer(text=f"Total creations: {gallery.total_generations} | Use !generate to make more")
            
            await ctx.send(embed=embed)
        
        async def _handle_help(ctx: commands.Context):
            """Handle help command."""
            embed = discord.Embed(
                title="🍌 BananaBot Commands v1.5",
                description="Your friendly AI image creation assistant",
                color=0xFFD700
            )
            
            embed.add_field(
                name="🎨 Create Images",
                value="`!generate <prompt>` - Create an image from your description\\n`!gallery` - View your recent creations\\n`!test` - Check if bot is working",
                inline=False
            )
            
            embed.add_field(
                name="💡 Tips",
                value="• Attach an image to `!generate` to edit it\\n• Use detailed prompts for better results\\n• All your images are saved in your personal gallery\\n• Try different art styles in your prompts",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Important",
                value="• Use `!` commands (not `/` commands)\\n• Old slash commands have been removed\\n• Type `!help` to see this message",
                inline=False
            )
            
            embed.set_footer(text="Made with 🍌 | v1.5 • All slash commands purged | Powered by Google Gemini")
            
            await ctx.send(embed=embed)
        
        # Bind methods to self
        self._handle_generate = _handle_generate
        self._handle_gallery = _handle_gallery  
        self._handle_help = _handle_help
        
    
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
        
        
        @self.command(name='help', aliases=['h'])
        async def help_command(ctx: commands.Context):
            """Show help information."""
            await self._handle_help(ctx)
        
        @self.command(name='test', aliases=['ping'])
        async def test_command(ctx: commands.Context):
            """Test if the bot is responding to commands."""
            await ctx.send("🍌 Bot is working! v1.5 - All slash command files deleted!")
    
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
            # First add command handlers
            self._add_command_handlers()
            
            # Then add prefix commands
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
        
        # CRITICAL: Clear any old slash commands by syncing empty tree
        try:
            await self.tree.sync()  # Sync empty tree to clear all slash commands
            logger.info("✅ Cleared all slash commands from Discord by syncing empty tree")
        except Exception as e:
            logger.error(f"Failed to clear slash commands: {e}")
        
        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="for !generate commands"
            ),
            status=discord.Status.online
        )
        
        # Log prefix commands status
        commands = [cmd.name for cmd in self.commands]
        logger.info(f"Loaded {len(commands)} prefix commands: {commands}")
    
    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Handle general bot errors."""
        logger.error(f"Error in {event_method}")
        error_handler.log_error(Exception(f"Bot error in {event_method}"))
    
    
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
    
    logger.info("Bot created successfully with prefix commands")
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