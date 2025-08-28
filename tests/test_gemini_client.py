"""Tests for Gemini API client."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import io
from PIL import Image

from bot.services.gemini_client import GeminiImageClient
from bot.utils.error_handler import GeminiAPIError, ContentFilterError


class TestGeminiImageClient:
    """Test cases for GeminiImageClient."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a GeminiImageClient with mocked dependencies."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            client = GeminiImageClient("fake_api_key")
            return client, mock_genai
    
    def test_client_initialization(self):
        """Test client initializes correctly."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            client = GeminiImageClient("test_key")
            assert client.api_key == "test_key"
            assert client.model == "gemini-2.5-flash-image-preview"
            mock_genai.configure.assert_called_once_with(api_key="test_key")
    
    def test_client_initialization_failure(self):
        """Test client initialization handles failures."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            mock_genai.configure.side_effect = Exception("API Error")
            
            with pytest.raises(GeminiAPIError, match="Failed to initialize"):
                GeminiImageClient("test_key")
    
    @pytest.mark.asyncio
    async def test_generate_image_success(self):
        """Test successful image generation."""
        client, mock_genai = self.mock_client()
        
        # Create fake image data
        fake_image_data = b"fake_image_data"
        
        with patch.object(client, '_generate_sync', return_value=fake_image_data) as mock_gen:
            result = await client.generate_image("test prompt")
            
            assert result == fake_image_data
            mock_gen.assert_called_once_with("test prompt")
    
    @pytest.mark.asyncio
    async def test_generate_image_retry_success(self):
        """Test image generation succeeds after retry."""
        client, mock_genai = self.mock_client()
        
        fake_image_data = b"fake_image_data"
        
        with patch.object(client, '_generate_sync') as mock_gen:
            # First call fails, second succeeds
            mock_gen.side_effect = [Exception("Temporary error"), fake_image_data]
            
            result = await client.generate_image("test prompt", retry_count=2)
            
            assert result == fake_image_data
            assert mock_gen.call_count == 2
    
    @pytest.mark.asyncio
    async def test_generate_image_retry_exhausted(self):
        """Test image generation fails after exhausting retries."""
        client, mock_genai = self.mock_client()
        
        with patch.object(client, '_generate_sync') as mock_gen:
            mock_gen.side_effect = Exception("Persistent error")
            
            with pytest.raises(GeminiAPIError, match="Failed to generate image after 3 attempts"):
                await client.generate_image("test prompt", retry_count=3)
            
            assert mock_gen.call_count == 3
    
    @pytest.mark.asyncio
    async def test_generate_image_content_filter_no_retry(self):
        """Test content filter errors are not retried."""
        client, mock_genai = self.mock_client()
        
        with patch.object(client, '_generate_sync') as mock_gen:
            mock_gen.side_effect = ContentFilterError("Blocked content")
            
            with pytest.raises(ContentFilterError, match="Blocked content"):
                await client.generate_image("bad prompt", retry_count=3)
            
            # Should not retry content filter errors
            assert mock_gen.call_count == 1
    
    @pytest.mark.asyncio
    async def test_edit_image_success(self):
        """Test successful image editing."""
        client, mock_genai = self.mock_client()
        
        fake_image_data = b"original_image"
        fake_edited_data = b"edited_image"
        
        with patch.object(client, '_edit_sync', return_value=fake_edited_data) as mock_edit:
            result = await client.edit_image("edit prompt", fake_image_data)
            
            assert result == fake_edited_data
            mock_edit.assert_called_once_with("edit prompt", fake_image_data)
    
    @pytest.mark.asyncio
    async def test_edit_image_retry(self):
        """Test image editing retry logic."""
        client, mock_genai = self.mock_client()
        
        fake_image_data = b"original_image"
        fake_edited_data = b"edited_image"
        
        with patch.object(client, '_edit_sync') as mock_edit:
            mock_edit.side_effect = [Exception("Temporary error"), fake_edited_data]
            
            result = await client.edit_image("edit prompt", fake_image_data, retry_count=2)
            
            assert result == fake_edited_data
            assert mock_edit.call_count == 2
    
    def test_generate_sync_success(self):
        """Test synchronous generation success."""
        client, mock_genai = self.mock_client()
        
        # Mock the response structure
        mock_part = Mock()
        mock_part.inline_data.data = b"image_data"
        
        mock_response = Mock()
        mock_response.prompt_feedback = None
        mock_response.parts = [mock_part]
        
        client.client.generate_content.return_value = mock_response
        
        result = client._generate_sync("test prompt")
        assert result == b"image_data"
    
    def test_generate_sync_content_filter(self):
        """Test synchronous generation with content filter."""
        client, mock_genai = self.mock_client()
        
        mock_feedback = Mock()
        mock_feedback.block_reason.name = "SAFETY"
        
        mock_response = Mock()
        mock_response.prompt_feedback = mock_feedback
        mock_response.parts = []
        
        client.client.generate_content.return_value = mock_response
        
        with pytest.raises(ContentFilterError, match="Prompt blocked by content filter"):
            client._generate_sync("inappropriate prompt")
    
    def test_generate_sync_no_image(self):
        """Test synchronous generation when no image is returned."""
        client, mock_genai = self.mock_client()
        
        mock_response = Mock()
        mock_response.prompt_feedback = None
        mock_response.parts = []
        
        client.client.generate_content.return_value = mock_response
        
        with pytest.raises(GeminiAPIError, match="No image data found"):
            client._generate_sync("test prompt")
    
    def test_edit_sync_success(self):
        """Test synchronous editing success."""
        client, mock_genai = self.mock_client()
        
        # Create fake image data
        fake_image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        fake_image.save(image_bytes, format='PNG')
        image_data = image_bytes.getvalue()
        
        # Mock the response
        mock_part = Mock()
        mock_part.inline_data.data = b"edited_image_data"
        
        mock_response = Mock()
        mock_response.prompt_feedback = None
        mock_response.parts = [mock_part]
        
        client.client.generate_content.return_value = mock_response
        
        result = client._edit_sync("edit prompt", image_data)
        assert result == b"edited_image_data"
    
    def test_edit_sync_content_filter(self):
        """Test synchronous editing with content filter."""
        client, mock_genai = self.mock_client()
        
        # Create fake image data
        fake_image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        fake_image.save(image_bytes, format='PNG')
        image_data = image_bytes.getvalue()
        
        mock_feedback = Mock()
        mock_feedback.block_reason.name = "SAFETY"
        
        mock_response = Mock()
        mock_response.prompt_feedback = mock_feedback
        mock_response.parts = []
        
        client.client.generate_content.return_value = mock_response
        
        with pytest.raises(ContentFilterError, match="Edit prompt blocked"):
            client._edit_sync("inappropriate edit", image_data)
    
    def test_validate_image_data_valid(self):
        """Test image data validation with valid data."""
        client, mock_genai = self.mock_client()
        
        # Create valid image data
        fake_image = Image.new('RGB', (100, 100), color='red')
        image_bytes = io.BytesIO()
        fake_image.save(image_bytes, format='PNG')
        image_data = image_bytes.getvalue()
        
        # Should not raise exception
        client._validate_image_data(image_data)
    
    def test_validate_image_data_invalid_format(self):
        """Test image data validation with invalid format."""
        client, mock_genai = self.mock_client()
        
        invalid_data = b"not_an_image"
        
        with pytest.raises(ValueError, match="Invalid image data"):
            client._validate_image_data(invalid_data)
    
    def test_validate_image_data_too_large(self):
        """Test image data validation with oversized image."""
        client, mock_genai = self.mock_client()
        
        # Create large fake image data (simulate 10MB file)
        large_data = b"x" * (10 * 1024 * 1024)
        
        # Mock PIL Image.open to return a fake image
        with patch('PIL.Image.open') as mock_open:
            mock_image = Mock()
            mock_image.format = 'PNG'
            mock_open.return_value = mock_image
            
            with pytest.raises(ValueError, match="Image too large"):
                client._validate_image_data(large_data)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check success."""
        client, mock_genai = self.mock_client()
        
        with patch.object(client, 'generate_image', return_value=b"test_data") as mock_gen:
            result = await client.health_check()
            assert result is True
            mock_gen.assert_called_once_with("test", retry_count=1)
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        client, mock_genai = self.mock_client()
        
        with patch.object(client, 'generate_image', side_effect=Exception("API down")) as mock_gen:
            result = await client.health_check()
            assert result is False


# Integration-style tests (still mocked but testing more complete flows)
class TestGeminiClientIntegration:
    """Integration tests for GeminiImageClient."""
    
    @pytest.mark.asyncio
    async def test_full_generation_flow(self):
        """Test complete image generation flow."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            # Setup client
            client = GeminiImageClient("test_key")
            
            # Mock successful API response
            mock_part = Mock()
            mock_part.inline_data.data = b"generated_image_data"
            
            mock_response = Mock()
            mock_response.prompt_feedback = None
            mock_response.parts = [mock_part]
            
            client.client.generate_content.return_value = mock_response
            
            # Test generation
            result = await client.generate_image("beautiful sunset")
            
            assert result == b"generated_image_data"
            client.client.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_full_edit_flow(self):
        """Test complete image editing flow."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            # Setup client
            client = GeminiImageClient("test_key")
            
            # Create test image
            test_image = Image.new('RGB', (100, 100), color='blue')
            img_bytes = io.BytesIO()
            test_image.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
            
            # Mock successful API response
            mock_part = Mock()
            mock_part.inline_data.data = b"edited_image_data"
            
            mock_response = Mock()
            mock_response.prompt_feedback = None
            mock_response.parts = [mock_part]
            
            client.client.generate_content.return_value = mock_response
            
            # Test editing
            result = await client.edit_image("add rainbow", image_data)
            
            assert result == b"edited_image_data"
            client.client.generate_content.assert_called_once()


# Performance and concurrency tests
class TestConcurrency:
    """Test concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_generations(self):
        """Test multiple concurrent image generations."""
        with patch('bot.services.gemini_client.genai') as mock_genai:
            client = GeminiImageClient("test_key")
            
            # Mock responses
            mock_part = Mock()
            mock_part.inline_data.data = b"concurrent_image"
            
            mock_response = Mock()
            mock_response.prompt_feedback = None
            mock_response.parts = [mock_part]
            
            client.client.generate_content.return_value = mock_response
            
            # Run concurrent generations
            tasks = [
                client.generate_image(f"image {i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 5
            assert all(result == b"concurrent_image" for result in results)
            
            # API should have been called 5 times
            assert client.client.generate_content.call_count == 5