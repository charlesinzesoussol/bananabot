"""Gemini API client wrapper with retry logic and error handling."""

import asyncio
import io
import logging
from PIL import Image
import google.generativeai as genai
from ..config import config
from ..utils.error_handler import GeminiAPIError, ContentFilterError

logger = logging.getLogger(__name__)

class GeminiImageClient:
    """
    Wrapper for Google Gemini 2.5 Flash Image API.
    
    Provides image generation and editing capabilities with retry logic,
    error handling, and content safety checks.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI Studio API key
        """
        self.api_key = api_key
        self.model = config.GEMINI_MODEL
        self._configure_client()
        
    def _configure_client(self) -> None:
        """Configure the Gemini client with API key and settings."""
        try:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(self.model)
            logger.info(f"Initialized Gemini client with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise GeminiAPIError(f"Failed to initialize Gemini client: {e}")
        return None
    
    async def generate_image(self, prompt: str, retry_count: int = 3) -> bytes:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            retry_count: Number of retry attempts on failure
            
        Returns:
            Image data as bytes in PNG format
            
        Raises:
            GeminiAPIError: If image generation fails after retries
            ContentFilterError: If prompt is blocked by content filter
        """
        logger.info(f"Generating image for prompt: '{prompt[:50]}...'")
        
        # PATTERN: Exponential backoff for retries
        for attempt in range(retry_count):
            try:
                # CRITICAL: Run in executor for blocking I/O
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    self._generate_sync,
                    prompt
                )
                logger.info("Image generated successfully")
                return response
                
            except ContentFilterError:
                # Don't retry content filter errors
                raise
                
            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                if attempt == retry_count - 1:
                    logger.error(f"All generation attempts failed for prompt: {prompt[:50]}...")
                    raise GeminiAPIError(f"Failed to generate image after {retry_count} attempts: {e}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        # Should never reach here, but mypy requires this
        raise GeminiAPIError(f"Failed to generate image after {retry_count} attempts")
    
    async def fuse_multiple_images(self, prompt: str, image_data_list: list[bytes], retry_count: int = 3) -> bytes:
        """
        Fuse/combine multiple images based on a text prompt.
        
        Args:
            prompt: Text description of how to combine/fuse the images
            image_data_list: List of image data as bytes (2-10 images recommended)
            retry_count: Number of retry attempts on failure
            
        Returns:
            Fused image data as bytes in PNG format
            
        Raises:
            GeminiAPIError: If image fusion fails after retries
            ContentFilterError: If prompt is blocked by content filter
        """
        logger.info(f"Fusing {len(image_data_list)} images with prompt: '{prompt[:50]}...'")
        
        if len(image_data_list) < 2:
            raise GeminiAPIError("At least 2 images required for fusion")
        if len(image_data_list) > 10:
            raise GeminiAPIError("Maximum 10 images allowed for fusion")
        
        # PATTERN: Exponential backoff for retries
        for attempt in range(retry_count):
            try:
                # Convert all images to PIL format
                pil_images = []
                for img_data in image_data_list:
                    try:
                        pil_image = Image.open(io.BytesIO(img_data))
                        # Convert to RGB if necessary
                        if pil_image.mode != 'RGB':
                            pil_image = pil_image.convert('RGB')
                        pil_images.append(pil_image)
                    except Exception as e:
                        raise GeminiAPIError(f"Failed to process image: {e}")
                
                # Create content list with prompt and all images
                content = [prompt] + pil_images
                
                # Generate fused image
                response = await asyncio.to_thread(
                    self.client.generate_content,
                    content
                )
                
                # Check for content filtering
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    raise ContentFilterError(f"Content filtered: {response.prompt_feedback.block_reason}")
                
                # Extract and return image data
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    
                    if hasattr(candidate, 'content') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data'):
                                image_data = part.inline_data.data
                                logger.info("Successfully fused multiple images")
                                return image_data
                
                raise GeminiAPIError("No image data in response")
                
            except ContentFilterError:
                raise  # Don't retry content filter errors
            except Exception as e:
                logger.warning(f"Image fusion attempt {attempt + 1} failed: {e}")
                if attempt < retry_count - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise GeminiAPIError(f"Failed to fuse images after {retry_count} attempts: {e}")
    
    async def edit_image(self, prompt: str, image_data: bytes, retry_count: int = 3) -> bytes:
        """
        Edit an existing image based on a text prompt.
        
        Args:
            prompt: Text description of the desired edit
            image_data: Original image data as bytes
            retry_count: Number of retry attempts on failure
            
        Returns:
            Edited image data as bytes in PNG format
            
        Raises:
            GeminiAPIError: If image editing fails after retries
            ContentFilterError: If prompt is blocked by content filter
        """
        logger.info(f"Editing image with prompt: '{prompt[:50]}...'")
        
        # PATTERN: Exponential backoff for retries
        for attempt in range(retry_count):
            try:
                # CRITICAL: Run in executor for blocking I/O
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    self._edit_sync,
                    prompt,
                    image_data
                )
                logger.info("Image edited successfully")
                return response
                
            except ContentFilterError:
                # Don't retry content filter errors
                raise
                
            except Exception as e:
                logger.warning(f"Edit attempt {attempt + 1} failed: {e}")
                if attempt == retry_count - 1:
                    logger.error(f"All edit attempts failed for prompt: {prompt[:50]}...")
                    raise GeminiAPIError(f"Failed to edit image after {retry_count} attempts: {e}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        # Should never reach here, but mypy requires this
        raise GeminiAPIError(f"Failed to edit image after {retry_count} attempts")
    
    def _generate_sync(self, prompt: str) -> bytes:
        """
        Synchronous image generation (runs in executor).
        
        Args:
            prompt: Text description of the image
            
        Returns:
            Image data as bytes
            
        Raises:
            ContentFilterError: If prompt is blocked
            GeminiAPIError: If generation fails
        """
        try:
            # GOTCHA: Gemini expects list format for contents
            response = self.client.generate_content([prompt])
            
            # Check for content filter blocks
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name
                raise ContentFilterError(f"Prompt blocked by content filter: {reason}")
            
            # PATTERN: Extract image from response parts
            if not response.parts:
                raise GeminiAPIError("No response parts received")
            
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # Handle inline image data
                    image_data = part.inline_data.data
                    return image_data
                elif hasattr(part, 'text') and 'base64' in part.text:
                    # Handle base64 encoded images in text
                    import base64
                    b64_data = part.text.split('base64,')[-1]
                    return base64.b64decode(b64_data)
            
            # If no image found, raise error
            raise GeminiAPIError("No image data found in response")
            
        except ContentFilterError:
            raise
        except Exception as e:
            logger.error(f"Sync generation error: {e}")
            raise GeminiAPIError(f"Generation failed: {e}")
    
    def _edit_sync(self, prompt: str, image_data: bytes) -> bytes:
        """
        Synchronous image editing (runs in executor).
        
        Args:
            prompt: Edit instruction
            image_data: Original image bytes
            
        Returns:
            Edited image data as bytes
            
        Raises:
            ContentFilterError: If prompt is blocked
            GeminiAPIError: If editing fails
        """
        try:
            # Convert bytes to PIL Image for Gemini
            image = Image.open(io.BytesIO(image_data))
            
            # Create edit prompt with image
            edit_prompt = f"Edit this image: {prompt}"
            
            # GOTCHA: Gemini expects specific format for image+text
            response = self.client.generate_content([edit_prompt, image])
            
            # Check for content filter blocks
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason.name
                raise ContentFilterError(f"Edit prompt blocked by content filter: {reason}")
            
            # PATTERN: Extract image from response parts
            if not response.parts:
                raise GeminiAPIError("No response parts received")
            
            for part in response.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    return part.inline_data.data
                elif hasattr(part, 'text') and 'base64' in part.text:
                    import base64
                    b64_data = part.text.split('base64,')[-1]
                    return base64.b64decode(b64_data)
            
            raise GeminiAPIError("No edited image data found in response")
            
        except ContentFilterError:
            raise
        except Exception as e:
            logger.error(f"Sync edit error: {e}")
            raise GeminiAPIError(f"Edit failed: {e}")
    
    def _validate_image_data(self, image_data: bytes) -> None:
        """
        Validate image data format and size.
        
        Args:
            image_data: Image bytes to validate
            
        Raises:
            ValueError: If image is invalid or too large
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Check format
            if image.format not in config.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported image format: {image.format}")
            
            # Check size
            size_mb = len(image_data) / (1024 * 1024)
            if size_mb > config.MAX_IMAGE_SIZE_MB:
                raise ValueError(f"Image too large: {size_mb:.1f}MB (max: {config.MAX_IMAGE_SIZE_MB}MB)")
                
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}")
    
    async def health_check(self) -> bool:
        """
        Check if the Gemini API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple test generation
            await self.generate_image("test", retry_count=1)
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False