"""Input validation and content filtering utilities."""

import re
import logging
from typing import Tuple
from ..config import config
from ..utils.error_handler import ValidationError

logger = logging.getLogger(__name__)

class ContentValidator:
    """Validates and filters user input for safety and compliance."""
    
    # Banned words/phrases (expand as needed)
    BANNED_WORDS = [
        # Add inappropriate content filters here
        # This is a minimal example - production should use comprehensive lists
        "nsfw", "explicit", "nude", "naked", "sexual"
    ]
    
    # Prompt requirements
    MIN_PROMPT_LENGTH = 1
    MAX_PROMPT_LENGTH = 1000
    
    @staticmethod
    def validate_prompt(prompt: str) -> Tuple[bool, str]:
        """
        Validate text prompt for image generation.
        
        Args:
            prompt: User-provided text prompt
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not prompt or not prompt.strip():
            return False, "Prompt cannot be empty"
        
        prompt = prompt.strip()
        
        # Check length
        if len(prompt) < ContentValidator.MIN_PROMPT_LENGTH:
            return False, f"Prompt too short (min {ContentValidator.MIN_PROMPT_LENGTH} characters)"
        
        if len(prompt) > ContentValidator.MAX_PROMPT_LENGTH:
            return False, f"Prompt too long (max {ContentValidator.MAX_PROMPT_LENGTH} characters)"
        
        # Content filtering (if enabled)
        if config.ENABLE_CONTENT_FILTER:
            is_safe, error_msg = ContentValidator._check_content_safety(prompt)
            if not is_safe:
                return False, error_msg
        
        # Check for special characters that might cause issues
        if ContentValidator._has_problematic_chars(prompt):
            return False, "Prompt contains potentially problematic characters"
        
        return True, ""
    
    @staticmethod
    def _check_content_safety(text: str) -> Tuple[bool, str]:
        """
        Check if text contains inappropriate content.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_safe, error_message)
        """
        text_lower = text.lower()
        
        # Check against banned words
        for word in ContentValidator.BANNED_WORDS:
            if word.lower() in text_lower:
                logger.warning(f"Content filter triggered by word: {word}")
                return False, "Content filtered - please use appropriate language"
        
        # Check for repeated characters (spam detection)
        if re.search(r'(.)\1{10,}', text):  # 10+ repeated characters
            return False, "Text contains excessive repeated characters"
        
        # Check for excessive caps
        if len(text) > 20 and sum(1 for c in text if c.isupper()) > len(text) * 0.7:
            return False, "Please reduce the use of capital letters"
        
        return True, ""
    
    @staticmethod
    def _has_problematic_chars(text: str) -> bool:
        """
        Check for characters that might cause API or processing issues.
        
        Args:
            text: Text to check
            
        Returns:
            True if problematic characters found
        """
        # Check for control characters (except common whitespace)
        control_chars = [c for c in text if ord(c) < 32 and c not in '\t\n\r ']
        if control_chars:
            return True
        
        # Check for excessive special characters
        special_count = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if special_count > len(text) * 0.5:  # More than 50% special characters
            return True
        
        return False
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Clean and sanitize a prompt while preserving meaning.
        
        Args:
            prompt: Original prompt
            
        Returns:
            Sanitized prompt
        """
        if not prompt:
            return ""
        
        # Basic cleaning
        prompt = prompt.strip()
        
        # Remove excessive whitespace
        prompt = re.sub(r'\s+', ' ', prompt)
        
        # Remove control characters (keep basic whitespace)
        prompt = ''.join(c for c in prompt if ord(c) >= 32 or c in '\t\n ')
        
        # Limit consecutive punctuation
        prompt = re.sub(r'([.!?]){3,}', r'\1\1', prompt)
        
        return prompt
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """
        Validate filename for safety.
        
        Args:
            filename: Proposed filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return False, "Filename cannot be empty"
        
        # Check length
        if len(filename) > 255:
            return False, "Filename too long"
        
        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        if re.search(invalid_chars, filename):
            return False, "Filename contains invalid characters"
        
        # Check for reserved names (Windows)
        reserved = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        name_without_ext = filename.split('.')[0].upper()
        if name_without_ext in reserved:
            return False, "Filename uses reserved name"
        
        return True, ""
    
    @staticmethod
    def get_safe_filename(base_name: str, extension: str = "png") -> str:
        """
        Generate a safe filename.
        
        Args:
            base_name: Base name for the file
            extension: File extension (without dot)
            
        Returns:
            Safe filename
        """
        # Sanitize base name
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', base_name)
        safe_name = safe_name.strip('. ')  # Remove leading/trailing dots and spaces
        
        # Limit length (save space for extension)
        max_base_len = 240 - len(extension)
        if len(safe_name) > max_base_len:
            safe_name = safe_name[:max_base_len]
        
        # Ensure it's not empty
        if not safe_name:
            safe_name = "generated"
        
        return f"{safe_name}.{extension}"

def validate_prompt(prompt: str) -> bool:
    """
    Simple prompt validation function.
    
    Args:
        prompt: Text prompt to validate
        
    Returns:
        True if valid, raises ValidationError if invalid
        
    Raises:
        ValidationError: If prompt is invalid
    """
    is_valid, error_msg = ContentValidator.validate_prompt(prompt)
    if not is_valid:
        raise ValidationError(error_msg)
    return True

def validate_and_sanitize_prompt(prompt: str) -> str:
    """
    Validate and sanitize a prompt.
    
    Args:
        prompt: Original prompt
        
    Returns:
        Sanitized prompt
        
    Raises:
        ValidationError: If prompt is invalid even after sanitization
    """
    # First sanitize
    sanitized = ContentValidator.sanitize_prompt(prompt)
    
    # Then validate
    is_valid, error_msg = ContentValidator.validate_prompt(sanitized)
    if not is_valid:
        raise ValidationError(error_msg)
    
    return sanitized

# Global validator instance
validator = ContentValidator()