"""BananaBot v2 - Prefix-based Discord Image Generation Bot."""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Optional
import discord
from discord.ext import commands
import io

from .config import config
from .services.gemini_client import GeminiImageClient
from .services.batch_client import BatchImageClient
from .services.image_processor import ImageProcessor
from .utils.rate_limiter import RateLimiter
from .utils.error_handler import error_handler
from .models import UserGallery, ImageWork, BatchRequest, UserStats

logger = logging.getLogger(__name__)

class BananaBot(commands.Bot):
    """
    BananaBot v2 - Modern AI Image Generation Bot.
    
    Features:
    - !create <prompt> - Generate images
    - !edit <prompt> [image] - Edit images  
    - !gallery - View your works
    - !redo <number> - Modify previous work
    - !batch <prompt1> | <prompt2> - Bulk generation
    """
    
    def __init__(self):
        """Initialize BananaBot with prefix commands."""
        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True  # Required for prefix commands
        
        # Initialize bot with ! prefix
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,  # We'll create a custom help
            case_insensitive=True
        )
        
        # Initialize services
        self.gemini_client: Optional[GeminiImageClient] = None
        self.batch_client: Optional[BatchImageClient] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.image_processor = ImageProcessor()
        
        logger.info("BananaBot v2 initialized with prefix commands")
    
    async def setup_hook(self) -> None:
        """Setup bot services and commands."""
        logger.info("Setting up BananaBot v2...")
        
        try:
            # Initialize services
            self.gemini_client = GeminiImageClient(config.GEMINI_API_KEY)
            self.batch_client = BatchImageClient(config.GEMINI_API_KEY)
            self.rate_limiter = RateLimiter(
                max_requests=config.MAX_REQUESTS_PER_HOUR,
                window_hours=1
            )
            
            # Test API connection
            logger.info("Testing Gemini API connection...")
            # health_check would be implemented for quick test
            
            logger.info("BananaBot v2 setup complete!")
            
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            raise
    
    async def on_ready(self):
        """Called when bot is ready."""
        if self.user:
            logger.info(f"🍌 BananaBot v2 is online!")
            logger.info(f"Logged in as: {self.user} (ID: {self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")
            
            # Set bot status
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="!help for commands"
                )
            )
            
            logger.info("Commands available: !create, !edit, !gallery, !redo, !batch, !help")
        else:
            logger.warning("Bot user is None after ready event")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❓ Unknown command! Use `!help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏱️ Command on cooldown. Try again in {error.retry_after:.1f}s")
        else:
            logger.error(f"Command error: {error}")
            await ctx.send("❌ Something went wrong! Please try again.")

# Initialize bot instance
bot = BananaBot()

@bot.command(name='help', aliases=['h'])
async def help_command(ctx):
    """Show available commands."""
    embed = discord.Embed(
        title="🍌 BananaBot Commands",
        description="AI Image Generation & Editing Bot",
        color=0xFFE135
    )
    
    embed.add_field(
        name="🎨 Generation",
        value="`!create <prompt>` - Generate an image\n`!batch <prompt1> | <prompt2>` - Bulk generate",
        inline=False
    )
    
    embed.add_field(
        name="✏️ Editing", 
        value="`!edit <prompt>` + attach image - Edit an image\n`!redo <number>` - Modify previous work",
        inline=False
    )
    
    embed.add_field(
        name="📁 Gallery",
        value="`!gallery` - View your recent works\n`!stats` - View your usage stats",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Examples",
        value="`!create a beautiful sunset over mountains`\n`!edit add a rainbow` (with image)\n`!batch sunset | mountain | ocean`",
        inline=False
    )
    
    embed.set_footer(text="Powered by Gemini 2.5 Flash Image")
    await ctx.send(embed=embed)

@bot.command(name='create', aliases=['generate', 'make'])
@commands.cooldown(1, 30, commands.BucketType.user)  # 1 per 30 seconds per user
async def create_image(ctx, *, prompt: str):
    """Generate an image from text prompt."""
    logger.info(f"Create command from {ctx.author}: '{prompt[:50]}...'")
    
    # Rate limiting check
    user_id = str(ctx.author.id)
    if not await bot.rate_limiter.check_user(user_id):
        status = await bot.rate_limiter.get_user_status(user_id)
        reset_time = status.get('reset_time', 0)
        minutes = int(reset_time // 60) if reset_time else 0
        await ctx.send(f"⏰ Rate limit exceeded! Try again in {minutes} minutes.")
        return
    
    # Send initial response
    message = await ctx.send("🎨 Creating your image... This may take a moment!")
    
    try:
        # Generate image
        image_bytes = await bot.gemini_client.generate_image(prompt)
        
        # Create work record
        work_id = str(uuid.uuid4())[:8]
        work = ImageWork(
            id=work_id,
            user_id=user_id,
            prompt=prompt,
            image_url=f"generated_{work_id}.png",
            generation_type="create"
        )
        
        # Save to user gallery
        gallery = UserGallery.load(user_id)
        gallery.add_work(work)
        
        # Update user stats
        stats = UserStats.load(user_id)
        stats.update_stats(work)
        
        # Create Discord file
        file = discord.File(
            io.BytesIO(image_bytes),
            filename=f"generated_{work_id}.png"
        )
        
        # Create result embed
        embed = discord.Embed(
            title="✨ Image Generated!",
            description=f"**Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
            color=0x00ff00
        )
        embed.add_field(name="Work ID", value=f"`{work_id}`", inline=True)
        embed.add_field(name="Cost", value="$0.0025", inline=True)
        embed.add_field(name="Modify", value=f"`!redo {work_id}`", inline=True)
        embed.set_footer(text="Use !gallery to see all your works")
        
        # Edit original message
        await message.edit(content=None, embed=embed, attachments=[file])
        
        logger.info(f"Image generated successfully for {ctx.author} - Work ID: {work_id}")
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        await message.edit(content="❌ Failed to generate image. Please try again!")

@bot.command(name='edit', aliases=['modify'])
@commands.cooldown(1, 30, commands.BucketType.user)
async def edit_image(ctx, *, prompt: str):
    """Edit an uploaded image with AI."""
    # Check for attached image
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach an image to edit! Example: `!edit add rainbow` + attach image")
        return
    
    attachment = ctx.message.attachments[0]
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        await ctx.send("❌ Please attach a valid image file (PNG, JPEG, WEBP)")
        return
    
    logger.info(f"Edit command from {ctx.author}: '{prompt[:50]}...' on {attachment.filename}")
    
    # Rate limiting
    user_id = str(ctx.author.id)
    if not await bot.rate_limiter.check_user(user_id):
        await ctx.send("⏰ Rate limit exceeded! Please wait before making another request.")
        return
    
    message = await ctx.send("✏️ Editing your image... This may take a moment!")
    
    try:
        # Download image
        image_data = await attachment.read()
        
        # Validate image
        is_valid, error_msg = bot.image_processor.validate_image(image_data)
        if not is_valid:
            await message.edit(content=f"❌ Image validation failed: {error_msg}")
            return
        
        # Edit image
        edited_bytes = await bot.gemini_client.edit_image(prompt, image_data)
        
        # Create work record
        work_id = str(uuid.uuid4())[:8]
        work = ImageWork(
            id=work_id,
            user_id=user_id,
            prompt=f"Edit: {prompt}",
            image_url=f"edited_{work_id}.png",
            generation_type="edit"
        )
        
        # Save to gallery and stats
        gallery = UserGallery.load(user_id)
        gallery.add_work(work)
        
        stats = UserStats.load(user_id)
        stats.update_stats(work)
        
        # Create Discord file
        file = discord.File(
            io.BytesIO(edited_bytes),
            filename=f"edited_{work_id}.png"
        )
        
        # Create result embed
        embed = discord.Embed(
            title="✨ Image Edited!",
            description=f"**Edit:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
            color=0x0099ff
        )
        embed.add_field(name="Work ID", value=f"`{work_id}`", inline=True)
        embed.add_field(name="Original", value=attachment.filename, inline=True)
        embed.add_field(name="Modify Again", value=f"`!redo {work_id}`", inline=True)
        
        await message.edit(content=None, embed=embed, attachments=[file])
        
        logger.info(f"Image edited successfully for {ctx.author} - Work ID: {work_id}")
        
    except Exception as e:
        logger.error(f"Image editing failed: {e}")
        await message.edit(content="❌ Failed to edit image. Please try again!")

@bot.command(name='gallery', aliases=['history', 'works'])
async def view_gallery(ctx):
    """View user's recent works."""
    user_id = str(ctx.author.id)
    gallery = UserGallery.load(user_id)
    
    if not gallery.works:
        await ctx.send("📁 Your gallery is empty! Use `!create` to generate your first image.")
        return
    
    recent_works = gallery.get_recent_works(limit=5)
    
    embed = discord.Embed(
        title=f"🎨 {ctx.author.display_name}'s Gallery",
        description=f"Showing {len(recent_works)} of {len(gallery.works)} total works",
        color=0xFFE135
    )
    
    for i, work in enumerate(recent_works, 1):
        prompt_preview = work.prompt[:50] + "..." if len(work.prompt) > 50 else work.prompt
        embed.add_field(
            name=f"{i}. Work ID: {work.id}",
            value=f"**{work.generation_type.title()}:** {prompt_preview}\n`!redo {work.id}` to modify",
            inline=False
        )
    
    embed.add_field(
        name="📊 Stats",
        value=f"Total: {gallery.total_generations} | Cost: ${gallery.total_cost:.3f}",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='redo', aliases=['modify', 'regen'])
@commands.cooldown(1, 30, commands.BucketType.user)
async def redo_work(ctx, work_id: str, *, new_prompt: Optional[str] = None):
    """Modify/regenerate previous work."""
    user_id = str(ctx.author.id)
    gallery = UserGallery.load(user_id)
    
    original_work = gallery.get_work_by_id(work_id)
    if not original_work:
        await ctx.send(f"❌ Work ID `{work_id}` not found in your gallery. Use `!gallery` to see your works.")
        return
    
    # Rate limiting
    if not await bot.rate_limiter.check_user(user_id):
        await ctx.send("⏰ Rate limit exceeded! Please wait before making another request.")
        return
    
    # Use new prompt or original
    prompt = new_prompt if new_prompt else original_work.prompt
    
    message = await ctx.send(f"🔄 Regenerating work `{work_id}`...")
    
    try:
        # Generate new version
        image_bytes = await bot.gemini_client.generate_image(prompt)
        
        # Create new work record
        new_work_id = str(uuid.uuid4())[:8]
        work = ImageWork(
            id=new_work_id,
            user_id=user_id,
            prompt=prompt,
            image_url=f"regen_{new_work_id}.png",
            generation_type="create",
            parent_id=work_id  # Link to original
        )
        
        gallery.add_work(work)
        
        stats = UserStats.load(user_id)
        stats.update_stats(work)
        
        file = discord.File(
            io.BytesIO(image_bytes),
            filename=f"regen_{new_work_id}.png"
        )
        
        embed = discord.Embed(
            title="🔄 Work Regenerated!",
            description=f"**New Prompt:** {prompt[:100]}{'...' if len(prompt) > 100 else ''}",
            color=0xff9900
        )
        embed.add_field(name="New Work ID", value=f"`{new_work_id}`", inline=True)
        embed.add_field(name="Based On", value=f"`{work_id}`", inline=True)
        
        await message.edit(content=None, embed=embed, attachments=[file])
        
    except Exception as e:
        logger.error(f"Redo failed: {e}")
        await message.edit(content="❌ Failed to regenerate work. Please try again!")

@bot.command(name='batch', aliases=['bulk'])
@commands.cooldown(1, 300, commands.BucketType.user)  # 5 minutes cooldown
async def batch_generate(ctx, *, prompts: str):
    """Generate multiple images in batch (cost savings)."""
    user_id = str(ctx.author.id)
    
    # Parse prompts (separated by |)
    prompt_list = [p.strip() for p in prompts.split('|') if p.strip()]
    
    if len(prompt_list) < 2:
        await ctx.send("❌ Batch needs at least 2 prompts! Separate with `|`\nExample: `!batch sunset | mountain | ocean`")
        return
    
    if len(prompt_list) > 10:
        await ctx.send("❌ Maximum 10 prompts per batch!")
        return
    
    # Rate limiting (batch counts as multiple requests)
    for _ in range(len(prompt_list)):
        if not await bot.rate_limiter.check_user(user_id):
            await ctx.send("⏰ Not enough rate limit remaining for this batch!")
            return
    
    batch_id = str(uuid.uuid4())[:8]
    message = await ctx.send(f"🚀 Starting batch generation... (ID: `{batch_id}`)\n**{len(prompt_list)} images** - **50% cost savings!**")
    
    try:
        # Submit batch to processing
        results = await bot.batch_client.process_batch(prompt_list, user_id, batch_id)
        
        # Create works for each result
        works = []
        for i, (prompt, image_bytes) in enumerate(results):
            work_id = f"{batch_id}_{i+1}"
            work = ImageWork(
                id=work_id,
                user_id=user_id,
                prompt=prompt,
                image_url=f"batch_{work_id}.png",
                generation_type="batch",
                batch_id=batch_id,
                cost=0.00125  # 50% discount
            )
            works.append((work, image_bytes))
        
        # Save all works
        gallery = UserGallery.load(user_id)
        stats = UserStats.load(user_id)
        
        for work, _ in works:
            gallery.add_work(work)
            stats.update_stats(work)
        
        # Send results
        embed = discord.Embed(
            title="✨ Batch Complete!",
            description=f"Generated {len(works)} images with **50% cost savings**",
            color=0x00ff00
        )
        embed.add_field(name="Batch ID", value=f"`{batch_id}`", inline=True)
        embed.add_field(name="Total Cost", value=f"${len(works) * 0.00125:.4f}", inline=True)
        embed.add_field(name="Savings", value=f"${len(works) * 0.00125:.4f}", inline=True)
        
        files = []
        for i, (work, image_bytes) in enumerate(works):
            files.append(discord.File(
                io.BytesIO(image_bytes),
                filename=f"batch_{work.id}.png"
            ))
        
        await message.edit(content=None, embed=embed, attachments=files[:4])  # Discord limit
        
        if len(files) > 4:
            # Send remaining files
            remaining = files[4:]
            await ctx.send(f"**Batch {batch_id} - Remaining Images:**", files=remaining)
        
        logger.info(f"Batch completed for {ctx.author} - {len(works)} images")
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        await message.edit(content="❌ Batch processing failed. Please try again!")

@bot.command(name='stats')
async def user_stats(ctx):
    """Show user statistics."""
    user_id = str(ctx.author.id)
    stats = UserStats.load(user_id)
    
    if stats.total_generations == 0:
        await ctx.send("📊 No usage stats yet! Use `!create` to get started.")
        return
    
    embed = discord.Embed(
        title=f"📊 {ctx.author.display_name}'s Stats",
        color=0xFFE135
    )
    
    embed.add_field(name="🎨 Generations", value=str(stats.total_generations), inline=True)
    embed.add_field(name="✏️ Edits", value=str(stats.total_edits), inline=True)
    embed.add_field(name="🚀 Batches", value=str(stats.total_batches), inline=True)
    
    embed.add_field(name="💰 Total Cost", value=f"${stats.total_cost:.3f}", inline=True)
    embed.add_field(name="💵 Savings", value=f"${stats.total_savings:.3f}", inline=True)
    
    if stats.first_generation:
        embed.add_field(
            name="📅 Member Since", 
            value=stats.first_generation.strftime("%B %d, %Y"),
            inline=True
        )
    
    await ctx.send(embed=embed)

# Error handlers and utility functions
async def main():
    """Main bot runner."""
    try:
        logger.info("Starting BananaBot v2...")
        
        # Validate config
        config.validate_config()
        config.setup_logging()
        
        # Start bot
        await bot.start(config.DISCORD_TOKEN)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())