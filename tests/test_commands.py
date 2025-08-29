"""Tests for Discord bot prefix commands."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import discord
from discord.ext import commands

from bot.main import create_bot


class TestPrefixCommands:
    """Test the prefix command system."""
    
    @pytest.fixture
    async def bot(self):
        """Create a test bot instance."""
        with patch('bot.config.config.validate_config'):
            with patch('bot.config.config.setup_logging'):
                bot = create_bot()
                bot._add_command_handlers()
                bot._add_prefix_commands()
                yield bot
                await bot.close()
    
    @pytest.mark.asyncio
    async def test_bot_has_commands(self, bot):
        """Test that the bot loads the expected commands."""
        command_names = [cmd.name for cmd in bot.commands]
        
        assert 'generate' in command_names
        assert 'gallery' in command_names
        assert 'help' in command_names
        assert 'test' in command_names
        
        # Should have exactly 4 commands
        assert len(command_names) == 4
    
    @pytest.mark.asyncio 
    async def test_generate_command_exists(self, bot):
        """Test that generate command is registered."""
        generate_cmd = bot.get_command('generate')
        assert generate_cmd is not None
        assert 'g' in generate_cmd.aliases
        assert 'create' in generate_cmd.aliases
    
    @pytest.mark.asyncio
    async def test_gallery_command_exists(self, bot):
        """Test that gallery command is registered."""
        gallery_cmd = bot.get_command('gallery')
        assert gallery_cmd is not None
        assert 'history' in gallery_cmd.aliases
        assert 'works' in gallery_cmd.aliases
    
    @pytest.mark.asyncio
    async def test_help_command_exists(self, bot):
        """Test that help command is registered."""
        help_cmd = bot.get_command('help')
        assert help_cmd is not None
        assert 'h' in help_cmd.aliases
    
    @pytest.mark.asyncio
    async def test_test_command_exists(self, bot):
        """Test that test command is registered."""
        test_cmd = bot.get_command('test')
        assert test_cmd is not None
        assert 'ping' in test_cmd.aliases


class TestCommandHandlers:
    """Test command handler functionality."""
    
    def test_bot_creation(self):
        """Test that bot can be created without errors."""
        with patch('bot.config.config.validate_config'):
            with patch('bot.config.config.setup_logging'):
                bot = create_bot()
                assert bot is not None
                assert isinstance(bot, commands.Bot)
                assert bot.command_prefix == '!'