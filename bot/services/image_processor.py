"""Image processing and validation utilities."""

import io
import logging
from typing import Tuple, Optional
from PIL import Image
from PIL.Image import Image as PILImage
import discord
from ..config import config
from ..utils.error_handler import ImageProcessingError, ValidationError

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Handle image processing, validation, and Discord integration."""
    
    @staticmethod
    def validate_image(image_data: bytes) -> Tuple[bool, str]:
        """
        Validate image data format and size.
        
        Args:
            image_data: Image bytes to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Check format
            if image.format not in config.SUPPORTED_FORMATS:
                return False, f"Unsupported format: {image.format}. Supported: {', '.join(config.SUPPORTED_FORMATS)}"
            
            # Check size
            size_mb = len(image_data) / (1024 * 1024)
            if size_mb > config.MAX_IMAGE_SIZE_MB:
                return False, f"Image too large: {size_mb:.1f}MB (max: {config.MAX_IMAGE_SIZE_MB}MB)"
            
            # Check dimensions (optional, prevent extremely large images)
            max_dimension = 4096  # Reasonable max for Discord/Gemini
            if image.width > max_dimension or image.height > max_dimension:
                return False, f"Image dimensions too large: {image.width}x{image.height} (max: {max_dimension}x{max_dimension})"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid image data: {e}"
    
    @staticmethod
    def optimize_image(image_data: bytes, max_size_mb: Optional[float] = None) -> bytes:
        """
        Optimize image for Discord upload.
        
        Args:
            image_data: Original image bytes
            max_size_mb: Maximum size in MB (defaults to Discord limit)
            
        Returns:
            Optimized image bytes
            
        Raises:
            ImageProcessingError: If optimization fails
        """
        if max_size_mb is None:
            max_size_mb = config.MAX_IMAGE_SIZE_MB
            
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Start with high quality
            quality = 95
            
            while quality > 20:  # Don't go below 20% quality
                buffer = io.BytesIO()
                
                # Convert to RGB if necessary (for JPEG)
                if image.mode in ('RGBA', 'P'):
                    # Keep PNG format for transparent images
                    image.save(buffer, format='PNG', optimize=True)
                else:
                    # Use JPEG for opaque images (better compression)
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    image.save(buffer, format='JPEG', quality=quality, optimize=True)
                
                result_data = buffer.getvalue()
                size_mb = len(result_data) / (1024 * 1024)
                
                if size_mb <= max_size_mb:
                    logger.info(f"Optimized image to {size_mb:.1f}MB (quality: {quality})")
                    return result_data
                
                quality -= 10
            
            # If still too large, try resizing
            logger.warning("Quality reduction insufficient, trying resize")
            return ImageProcessor._resize_image(image, max_size_mb)
            
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            raise ImageProcessingError(f"Failed to optimize image: {e}")
    
    @staticmethod
    def _resize_image(image: PILImage, max_size_mb: float) -> bytes:
        """
        Resize image to fit within size limit.
        
        Args:
            image: PIL Image object
            max_size_mb: Maximum size in MB
            
        Returns:
            Resized image bytes
        """
        scale_factor = 0.8
        
        while scale_factor > 0.3:  # Don't resize below 30% of original
            new_width = int(image.width * scale_factor)
            new_height = int(image.height * scale_factor)
            
            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            if resized.mode in ('RGBA', 'P'):
                resized.save(buffer, format='PNG', optimize=True)
            else:
                if resized.mode != 'RGB':
                    resized = resized.convert('RGB')
                resized.save(buffer, format='JPEG', quality=85, optimize=True)
            
            result_data = buffer.getvalue()
            size_mb = len(result_data) / (1024 * 1024)
            
            if size_mb <= max_size_mb:
                logger.info(f"Resized image to {new_width}x{new_height} ({size_mb:.1f}MB)")
                return result_data
            
            scale_factor -= 0.1
        
        raise ImageProcessingError("Unable to reduce image size sufficiently")
    
    @staticmethod
    async def download_attachment(attachment: discord.Attachment) -> bytes:
        """
        Download Discord attachment.
        
        Args:
            attachment: Discord attachment object
            
        Returns:
            Attachment data as bytes
            
        Raises:
            ImageProcessingError: If download fails
        """
        try:
            if attachment.size > config.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Attachment too large: {attachment.size / (1024*1024):.1f}MB")
            
            data = await attachment.read()
            logger.info(f"Downloaded attachment: {attachment.filename} ({len(data)} bytes)")
            return data
            
        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            raise ImageProcessingError(f"Failed to download image: {e}")
    
    @staticmethod
    def create_discord_file(image_data: bytes, filename: str = "generated.png") -> discord.File:
        """
        Create Discord file from image data.
        
        Args:
            image_data: Image bytes
            filename: Filename for the attachment
            
        Returns:
            Discord File object
            
        Raises:
            ImageProcessingError: If file creation fails
        """
        try:
            # Validate image first
            is_valid, error_msg = ImageProcessor.validate_image(image_data)
            if not is_valid:
                raise ValidationError(error_msg)
            
            # Optimize if needed
            size_mb = len(image_data) / (1024 * 1024)
            if size_mb > config.MAX_IMAGE_SIZE_MB:
                logger.info(f"Optimizing image ({size_mb:.1f}MB)")
                image_data = ImageProcessor.optimize_image(image_data)
            
            # Create Discord file
            file = discord.File(
                io.BytesIO(image_data),
                filename=filename
            )
            logger.info(f"Created Discord file: {filename}")
            return file
            
        except Exception as e:
            logger.error(f"Failed to create Discord file: {e}")
            raise ImageProcessingError(f"Failed to create file: {e}")
    
    @staticmethod
    def get_image_info(image_data: bytes) -> dict:
        """
        Get information about an image.
        
        Args:
            image_data: Image bytes
            
        Returns:
            Dictionary with image information
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            size_mb = len(image_data) / (1024 * 1024)
            
            return {
                'format': image.format,
                'size': f"{image.width}x{image.height}",
                'mode': image.mode,
                'size_mb': round(size_mb, 2),
                'size_bytes': len(image_data)
            }
        except Exception as e:
            logger.error(f"Failed to get image info: {e}")
            return {'error': str(e)}

# Global image processor instance
image_processor = ImageProcessor()