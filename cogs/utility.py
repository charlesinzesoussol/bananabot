"""
Utility Cog - Help, info, and utility commands
"""

import logging
from typing import List

import discord
from discord.ext import commands
from discord.ext.commands import Context

logger = logging.getLogger(__name__)


class Utility(commands.Cog, name="utility"):
    """Utility and information commands."""

    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="help",
        description="Get help about the bot and its commands",
        aliases=["h"]
    )
    async def help(self, context: Context) -> None:
        """Display help information."""
        
        embed = discord.Embed(
            title="🍌 BananaBot v1.7",
            description="AI Image Generation Bot - Template Structure",
            color=0xFFD700
        )

        # Available commands
        embed.add_field(
            name="🍌 Available Commands",
            value=(
                "`!generate <prompt>` - Generate an AI image\n"
                "`!edit <prompt>` - Edit an attached image with AI\n"
                "`!gallery [limit]` - View your image gallery\n"
                "`!help` - Show this help message"
            ),
            inline=False
        )

        # Usage tips
        embed.add_field(
            name="💡 Tips",
            value=(
                "• Use `!edit` with an attached image to modify it\n"
                "• Use `!generate` for creating new images from text\n"
                "• Your gallery saves all your creations"
            ),
            inline=False
        )

        embed.set_footer(text="BananaBot - Simple AI Image Generation")
        await context.send(embed=embed)





async def setup(bot) -> None:
    """Setup function to add the cog to the bot."""
    await bot.add_cog(Utility(bot))