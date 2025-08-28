"""Tests for Discord bot commands."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import discord
import io
from PIL import Image

# Mock discord module for testing
discord.Interaction = Mock
discord.File = Mock
discord.Embed = Mock


class MockInteraction:
    """Mock Discord interaction for testing."""
    
    def __init__(self, user_id="123456789", guild_id="987654321"):
        self.user = Mock()
        self.user.id = user_id
        self.user.mention = f"<@{user_id}>"
        
        self.guild = Mock()
        self.guild.id = guild_id
        
        self.response = Mock()
        self.response.defer = AsyncMock()
        self.response.is_done.return_value = False
        self.response.send_message = AsyncMock()
        
        self.followup = Mock()
        self.followup.send = AsyncMock()
        
        self.command = Mock()
        self.command.name = "test_command"


class MockAttachment:
    """Mock Discord attachment for testing."""
    
    def __init__(self, filename="test.png", content_type="image/png", size=1024):
        self.filename = filename
        self.content_type = content_type
        self.size = size
        
        # Create fake image data
        fake_image = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        fake_image.save(img_bytes, format='PNG')
        self._data = img_bytes.getvalue()
    
    async def read(self):
        """Mock attachment read method."""
        return self._data


class MockBot:
    """Mock bot for testing commands."""
    
    def __init__(self):
        self.gemini_client = Mock()
        self.rate_limiter = Mock()
        self.tree = Mock()


class TestGenerateCommand:
    """Test cases for /generate command."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot for testing."""
        bot = MockBot()
        
        # Mock successful rate limiting
        bot.rate_limiter.check_user = AsyncMock(return_value=True)
        
        # Mock successful image generation
        bot.gemini_client.generate_image = AsyncMock(return_value=b"fake_image_data")
        
        return bot
    
    @pytest.mark.asyncio
    async def test_generate_command_success(self, mock_bot):
        """Test successful image generation."""
        from bot.commands.generate import setup_generate_command
        
        # Mock the image processor
        with patch('bot.commands.generate.image_processor') as mock_processor, \
             patch('bot.commands.generate.validator') as mock_validator:
            
            mock_validator.get_safe_filename.return_value = "generated_test.png"
            mock_processor.create_discord_file.return_value = Mock()
            
            # Setup command
            setup_generate_command(mock_bot)
            
            # Get the registered command function
            generate_func = mock_bot.tree.command.call_args[0][0]  # The decorated function
            
            # Create mock interaction
            interaction = MockInteraction()
            
            # Call the command
            await generate_func(interaction, "beautiful sunset")
            
            # Verify interactions
            interaction.response.defer.assert_called_once()
            mock_bot.rate_limiter.check_user.assert_called_once_with("123456789")
            mock_bot.gemini_client.generate_image.assert_called_once()
            interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_command_rate_limited(self, mock_bot):
        """Test generate command with rate limiting."""
        from bot.commands.generate import setup_generate_command
        
        # Mock rate limit exceeded
        mock_bot.rate_limiter.check_user = AsyncMock(return_value=False)
        mock_bot.rate_limiter.get_user_status = AsyncMock(return_value={
            'reset_time': 3600  # 1 hour
        })
        
        setup_generate_command(mock_bot)
        generate_func = mock_bot.tree.command.call_args[0][0]
        
        interaction = MockInteraction()
        await generate_func(interaction, "test prompt")
        
        # Should send rate limit message
        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "Rate limit exceeded" in call_args[0][0]
        assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_generate_command_invalid_prompt(self, mock_bot):
        """Test generate command with invalid prompt."""
        from bot.commands.generate import setup_generate_command
        
        # Mock validation failure
        with patch('bot.commands.generate.validate_and_sanitize_prompt') as mock_validate:
            from bot.utils.error_handler import ValidationError
            mock_validate.side_effect = ValidationError("Prompt too long")
            
            setup_generate_command(mock_bot)
            generate_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            await generate_func(interaction, "x" * 1001)  # Too long
            
            # Should send validation error
            interaction.followup.send.assert_called_once()
            call_args = interaction.followup.send.call_args
            assert "Invalid prompt" in call_args[0][0]
            assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_generate_command_api_failure(self, mock_bot):
        """Test generate command with API failure."""
        from bot.commands.generate import setup_generate_command
        
        # Mock API failure
        mock_bot.gemini_client.generate_image = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        with patch('bot.commands.generate.error_handler') as mock_error_handler:
            setup_generate_command(mock_bot)
            generate_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            await generate_func(interaction, "test prompt")
            
            # Should handle error
            mock_error_handler.handle_command_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_imagine_command_with_style(self, mock_bot):
        """Test /imagine command with preset style."""
        from bot.commands.generate import setup_generate_command
        
        with patch('bot.commands.generate.image_processor') as mock_processor, \
             patch('bot.commands.generate.validator') as mock_validator:
            
            mock_validator.get_safe_filename.return_value = "generated_test.png"
            mock_processor.create_discord_file.return_value = Mock()
            
            setup_generate_command(mock_bot)
            
            # Get the imagine command (second registered command)
            imagine_func = mock_bot.tree.command.call_args_list[1][0][0]
            
            interaction = MockInteraction()
            await imagine_func(interaction, "mountain landscape", "photorealistic")
            
            # Should generate with combined prompt
            mock_bot.gemini_client.generate_image.assert_called_once()
            call_args = mock_bot.gemini_client.generate_image.call_args[0][0]
            assert "photorealistic" in call_args


class TestEditCommand:
    """Test cases for /edit command."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot for testing."""
        bot = MockBot()
        bot.rate_limiter.check_user = AsyncMock(return_value=True)
        bot.gemini_client.edit_image = AsyncMock(return_value=b"fake_edited_data")
        return bot
    
    @pytest.mark.asyncio
    async def test_edit_command_success(self, mock_bot):
        """Test successful image editing."""
        from bot.commands.edit import setup_edit_command
        
        with patch('bot.commands.edit.image_processor') as mock_processor, \
             patch('bot.commands.edit.validator') as mock_validator:
            
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (True, "")
            mock_processor.create_discord_file.return_value = Mock()
            mock_validator.get_safe_filename.return_value = "edited_test.png"
            
            setup_edit_command(mock_bot)
            edit_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            attachment = MockAttachment()
            
            await edit_func(interaction, "add rainbow", attachment)
            
            # Verify interactions
            interaction.response.defer.assert_called_once()
            mock_bot.rate_limiter.check_user.assert_called_once_with("123456789")
            mock_processor.download_attachment.assert_called_once_with(attachment)
            mock_bot.gemini_client.edit_image.assert_called_once()
            interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_edit_command_invalid_attachment(self, mock_bot):
        """Test edit command with invalid attachment."""
        from bot.commands.edit import setup_edit_command
        
        setup_edit_command(mock_bot)
        edit_func = mock_bot.tree.command.call_args[0][0]
        
        interaction = MockInteraction()
        # Create attachment with invalid content type
        attachment = MockAttachment(content_type="text/plain")
        
        await edit_func(interaction, "test edit", attachment)
        
        # Should send error message
        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "valid image file" in call_args[0][0]
        assert call_args[1]['ephemeral'] is True
    
    @pytest.mark.asyncio
    async def test_edit_command_image_validation_failure(self, mock_bot):
        """Test edit command with image validation failure."""
        from bot.commands.edit import setup_edit_command
        
        with patch('bot.commands.edit.image_processor') as mock_processor:
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (False, "Image too large")
            
            setup_edit_command(mock_bot)
            edit_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            attachment = MockAttachment()
            
            await edit_func(interaction, "test edit", attachment)
            
            # Should send validation error
            interaction.followup.send.assert_called_once()
            call_args = interaction.followup.send.call_args
            assert "Image validation failed" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_inpaint_command(self, mock_bot):
        """Test /inpaint command functionality."""
        from bot.commands.edit import setup_edit_command
        
        with patch('bot.commands.edit.image_processor') as mock_processor, \
             patch('bot.commands.edit.validator') as mock_validator:
            
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (True, "")
            mock_processor.create_discord_file.return_value = Mock()
            mock_validator.get_safe_filename.return_value = "edited_test.png"
            
            setup_edit_command(mock_bot)
            
            # Get the inpaint command (second registered command)
            inpaint_func = mock_bot.tree.command.call_args_list[1][0][0]
            
            interaction = MockInteraction()
            attachment = MockAttachment()
            
            await inpaint_func(interaction, attachment, "car", "bicycle")
            
            # Should call edit with combined prompt
            mock_bot.gemini_client.edit_image.assert_called_once()
            call_args = mock_bot.gemini_client.edit_image.call_args[0][0]
            assert "Remove car and add bicycle" in call_args


class TestComposeCommand:
    """Test cases for /compose command."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot for testing."""
        bot = MockBot()
        bot.rate_limiter.check_user = AsyncMock(return_value=True)
        bot.gemini_client.edit_image = AsyncMock(return_value=b"fake_composed_data")
        return bot
    
    @pytest.mark.asyncio
    async def test_compose_command_success(self, mock_bot):
        """Test successful image composition."""
        from bot.commands.compose import setup_compose_command
        
        with patch('bot.commands.compose.image_processor') as mock_processor, \
             patch('bot.commands.compose.validator') as mock_validator:
            
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (True, "")
            mock_processor.create_discord_file.return_value = Mock()
            mock_validator.get_safe_filename.return_value = "composed_test.png"
            
            setup_compose_command(mock_bot)
            compose_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            attachment1 = MockAttachment("image1.png")
            attachment2 = MockAttachment("image2.png")
            
            await compose_func(interaction, "merge artistically", attachment1, attachment2)
            
            # Verify interactions
            interaction.response.defer.assert_called_once()
            mock_bot.rate_limiter.check_user.assert_called_once_with("123456789")
            
            # Should download both attachments
            assert mock_processor.download_attachment.call_count == 2
            
            mock_bot.gemini_client.edit_image.assert_called_once()
            interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_compose_command_with_optional_images(self, mock_bot):
        """Test compose command with optional third and fourth images."""
        from bot.commands.compose import setup_compose_command
        
        with patch('bot.commands.compose.image_processor') as mock_processor, \
             patch('bot.commands.compose.validator') as mock_validator:
            
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (True, "")
            mock_processor.create_discord_file.return_value = Mock()
            mock_validator.get_safe_filename.return_value = "composed_test.png"
            
            setup_compose_command(mock_bot)
            compose_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            attachments = [
                MockAttachment(f"image{i}.png") for i in range(1, 5)
            ]
            
            await compose_func(
                interaction, "create collage", 
                attachments[0], attachments[1], attachments[2], attachments[3]
            )
            
            # Should process all 4 images
            assert mock_processor.download_attachment.call_count == 4
    
    @pytest.mark.asyncio
    async def test_compose_command_invalid_attachment(self, mock_bot):
        """Test compose command with invalid attachment."""
        from bot.commands.compose import setup_compose_command
        
        setup_compose_command(mock_bot)
        compose_func = mock_bot.tree.command.call_args[0][0]
        
        interaction = MockInteraction()
        valid_attachment = MockAttachment()
        invalid_attachment = MockAttachment(content_type="text/plain")
        
        await compose_func(interaction, "test compose", valid_attachment, invalid_attachment)
        
        # Should send error message about invalid attachment
        interaction.followup.send.assert_called_once()
        call_args = interaction.followup.send.call_args
        assert "not a valid image file" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_collage_command(self, mock_bot):
        """Test /collage command functionality."""
        from bot.commands.compose import setup_compose_command
        
        with patch('bot.commands.compose.image_processor') as mock_processor, \
             patch('bot.commands.compose.validator') as mock_validator:
            
            mock_processor.download_attachment = AsyncMock(return_value=b"image_data")
            mock_processor.validate_image.return_value = (True, "")
            mock_processor.create_discord_file.return_value = Mock()
            mock_validator.get_safe_filename.return_value = "composed_test.png"
            
            setup_compose_command(mock_bot)
            
            # Get the collage command (second registered command)
            collage_func = mock_bot.tree.command.call_args_list[1][0][0]
            
            interaction = MockInteraction()
            attachment1 = MockAttachment("image1.png")
            attachment2 = MockAttachment("image2.png")
            
            await collage_func(interaction, attachment1, attachment2, style="vintage")
            
            # Should call compose with generated prompt
            mock_bot.gemini_client.edit_image.assert_called_once()
            call_args = mock_bot.gemini_client.edit_image.call_args[0][0]
            assert "vintage" in call_args
            assert "collage" in call_args


# Error handling tests
class TestCommandErrorHandling:
    """Test error handling across all commands."""
    
    @pytest.mark.asyncio
    async def test_command_handles_unexpected_errors(self):
        """Test that commands handle unexpected errors gracefully."""
        from bot.commands.generate import setup_generate_command
        
        mock_bot = MockBot()
        mock_bot.rate_limiter.check_user = AsyncMock(side_effect=Exception("Unexpected error"))
        
        with patch('bot.commands.generate.error_handler') as mock_error_handler:
            setup_generate_command(mock_bot)
            generate_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            await generate_func(interaction, "test prompt")
            
            # Should handle the error
            mock_error_handler.handle_command_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_command_handles_validation_errors_properly(self):
        """Test that validation errors are handled with proper user messages."""
        from bot.commands.generate import setup_generate_command
        from bot.utils.error_handler import ValidationError
        
        mock_bot = MockBot()
        
        with patch('bot.commands.generate.validate_and_sanitize_prompt') as mock_validate:
            mock_validate.side_effect = ValidationError("Test validation error", "User-friendly message")
            
            setup_generate_command(mock_bot)
            generate_func = mock_bot.tree.command.call_args[0][0]
            
            interaction = MockInteraction()
            await generate_func(interaction, "invalid prompt")
            
            # Should send user-friendly message
            interaction.followup.send.assert_called_once()
            call_args = interaction.followup.send.call_args
            assert "Invalid prompt" in call_args[0][0]