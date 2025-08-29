"""
Image Generation Cog - Handles all AI image generation commands
"""

import asyncio
import io
import logging
import uuid
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Context

from bot.models import UserGallery, ImageWork, UserStats


logger = logging.getLogger(__name__)


class ImageGeneration(commands.Cog, name="image_generation"):
    """Image generation commands using Gemini AI."""

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="generate",
        description="Generate an AI image from a text prompt",
        aliases=["g", "create", "gen"]
    )
    async def generate(self, context: Context, *, prompt: str) -> None:
        """
        Generate an image from a text prompt.
        
        Args:
            context: The command context
            prompt: Text description of the image to generate
        """
        user_id = str(context.author.id)

        # Check rate limit
        if not await self.bot.rate_limiter.check_user(user_id):
            embed = discord.Embed(
                title="Rate Limited",
                description="You're making requests too quickly. Please wait a moment and try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)
            return

        # Send initial response
        embed = discord.Embed(
            title="🎨 Generating Image",
            description=f"Creating: _{prompt}_",
            color=0xFFD700
        )
        await context.send(embed=embed)

        try:
            # For single prompts, use direct API (batch requires minimum 2 prompts)
            image_bytes = await self.bot.gemini_client.generate_image(prompt)

            # Save to user gallery
            gallery = UserGallery.load(user_id)
            work = ImageWork(
                id=str(uuid.uuid4())[:8],
                user_id=user_id,
                prompt=prompt,
                image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                generation_type="create",
                cost=0.0025  # Standard pricing for single generation
            )
            gallery.add_work(work)
            
            # Update user stats
            stats = UserStats.load(user_id)
            stats.update_stats(work)

            # Send final result
            file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
            
            embed = discord.Embed(
                title="🍌 Image Created!",
                description=f"**Prompt:** {prompt}",
                color=0x00FF00
            )
            embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
            embed.set_footer(text="Use !gallery to see all your works")
            
            await context.send(file=file, embed=embed)
            logger.info(f"Generated image for user {user_id}: {prompt}")

        except Exception as e:
            logger.error(f"Image generation failed for user {user_id}: {e}")
            embed = discord.Embed(
                title="Generation Failed",
                description="Sorry, image generation failed. Please try again with a different prompt.",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)

    @commands.hybrid_command(
        name="edit",
        description="Edit an attached image with AI",
        aliases=["e", "modify"]
    )
    async def edit(self, context: Context, *, prompt: str) -> None:
        """
        Edit an attached image using AI.
        
        Args:
            context: The command context
            prompt: Text description of the edits to make
        """
        user_id = str(context.author.id)

        # Check rate limit
        if not await self.bot.rate_limiter.check_user(user_id):
            embed = discord.Embed(
                title="Rate Limited",
                description="You're making requests too quickly. Please wait a moment and try again.",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)
            return

        # Check for attached images
        if not context.message.attachments:
            embed = discord.Embed(
                title="No Image Attached",
                description="Please attach an image to edit with this command.",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)
            return

        # Get the first image attachment
        image_data = None
        for attachment in context.message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_data = await attachment.read()
                break

        if not image_data:
            embed = discord.Embed(
                title="Invalid Attachment",
                description="Please attach a valid image file (PNG, JPG, etc.).",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)
            return

        # Send initial response
        embed = discord.Embed(
            title="🎨 Editing Image",
            description=f"Applying: _{prompt}_",
            color=0xFFD700
        )
        await context.send(embed=embed)

        try:
            # Edit the attached image
            image_bytes = await self.bot.gemini_client.edit_image(
                image_data=image_data,
                edit_prompt=prompt
            )

            # Save to user gallery
            gallery = UserGallery.load(user_id)
            work = ImageWork(
                id=str(uuid.uuid4())[:8],
                user_id=user_id,
                prompt=prompt,
                image_url=f"work_{str(uuid.uuid4())[:8]}.png",
                generation_type="edit",
                cost=0.0025  # Standard pricing for single generation
            )
            gallery.add_work(work)
            
            # Update user stats
            stats = UserStats.load(user_id)
            stats.update_stats(work)

            # Send final result
            file = discord.File(io.BytesIO(image_bytes), filename=f"{work.id}.png")
            
            embed = discord.Embed(
                title="🍌 Image Edited!",
                description=f"**Edit:** {prompt}",
                color=0x00FF00
            )
            embed.add_field(name="Work ID", value=f"`{work.id}`", inline=True)
            embed.set_footer(text="Use !gallery to see all your works")
            
            await context.send(file=file, embed=embed)
            logger.info(f"Edited image for user {user_id}: {prompt}")

        except Exception as e:
            logger.error(f"Image edit failed for user {user_id}: {e}")
            embed = discord.Embed(
                title="Edit Failed",
                description="Sorry, image editing failed. Please try again with a different image or prompt.",
                color=0xE02B2B
            )
            await context.send(embed=embed, delete_after=10)

    @commands.hybrid_command(
        name="gallery",
        description="View your recent image creations",
        aliases=["history", "works", "images"]
    )
    async def gallery(self, context: Context, limit: int = 5) -> None:
        """
        Display the user's recent image gallery.
        
        Args:
            context: The command context
            limit: Number of recent works to show (default 5, max 10)
        """
        user_id = str(context.author.id)
        limit = min(max(limit, 1), 10)  # Clamp between 1-10

        gallery = UserGallery.load(user_id)
        recent_works = gallery.get_recent_works(limit)

        if not recent_works:
            embed = discord.Embed(
                title="Empty Gallery",
                description="You haven't created any images yet! Use `!generate` to create your first one.",
                color=0x9932CC
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"🖼️ {context.author.display_name}'s Gallery",
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
        embed.set_footer(text="Use !generate to create more images")

        await context.send(embed=embed)



async def setup(bot) -> None:
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ImageGeneration(bot))