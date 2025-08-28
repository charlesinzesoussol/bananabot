"""Tests for input validation utilities."""

import pytest
from bot.utils.validators import (
    ContentValidator,
    validate_prompt,
    validate_and_sanitize_prompt,
    validator
)
from bot.utils.error_handler import ValidationError


class TestContentValidator:
    """Test cases for ContentValidator class."""
    
    def test_validate_prompt_valid(self):
        """Test valid prompt passes validation."""
        is_valid, error_msg = ContentValidator.validate_prompt("Generate a beautiful sunset")
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_prompt_empty(self):
        """Test empty prompt fails validation."""
        is_valid, error_msg = ContentValidator.validate_prompt("")
        assert is_valid is False
        assert "empty" in error_msg.lower()
        
        is_valid, error_msg = ContentValidator.validate_prompt("   ")
        assert is_valid is False
        assert "empty" in error_msg.lower()
    
    def test_validate_prompt_too_short(self):
        """Test prompt that's too short fails validation."""
        # This test assumes MIN_PROMPT_LENGTH is 1, so single character should pass
        is_valid, error_msg = ContentValidator.validate_prompt("a")
        assert is_valid is True
        
        # But empty should fail
        is_valid, error_msg = ContentValidator.validate_prompt("")
        assert is_valid is False
    
    def test_validate_prompt_too_long(self):
        """Test prompt that's too long fails validation."""
        long_prompt = "x" * 1001  # Exceeds MAX_PROMPT_LENGTH
        is_valid, error_msg = ContentValidator.validate_prompt(long_prompt)
        assert is_valid is False
        assert "too long" in error_msg.lower()
    
    def test_validate_prompt_max_length_boundary(self):
        """Test prompt at exactly max length."""
        max_length_prompt = "x" * 1000  # Exactly MAX_PROMPT_LENGTH
        is_valid, error_msg = ContentValidator.validate_prompt(max_length_prompt)
        assert is_valid is True
        assert error_msg == ""
    
    def test_content_safety_check_inappropriate(self):
        """Test content filter catches inappropriate content."""
        # Test with banned words
        for banned_word in ["nsfw", "explicit"]:
            is_safe, error_msg = ContentValidator._check_content_safety(f"Generate {banned_word} image")
            assert is_safe is False
            assert "content filtered" in error_msg.lower()
    
    def test_content_safety_check_repeated_chars(self):
        """Test content filter catches excessive repeated characters."""
        is_safe, error_msg = ContentValidator._check_content_safety("aaaaaaaaaaaaa")  # 13 'a's
        assert is_safe is False
        assert "repeated characters" in error_msg.lower()
    
    def test_content_safety_check_excessive_caps(self):
        """Test content filter catches excessive caps."""
        caps_text = "GENERATE A VERY LOUD IMAGE WITH LOTS OF SHOUTING"
        is_safe, error_msg = ContentValidator._check_content_safety(caps_text)
        assert is_safe is False
        assert "capital letters" in error_msg.lower()
    
    def test_content_safety_check_valid(self):
        """Test content filter passes valid content."""
        is_safe, error_msg = ContentValidator._check_content_safety("A beautiful mountain landscape")
        assert is_safe is True
        assert error_msg == ""
    
    def test_has_problematic_chars_control_chars(self):
        """Test detection of problematic control characters."""
        text_with_control = "Normal text\x00with control"
        assert ContentValidator._has_problematic_chars(text_with_control) is True
        
        # But normal whitespace should be fine
        text_with_whitespace = "Normal text\n\twith whitespace"
        assert ContentValidator._has_problematic_chars(text_with_whitespace) is False
    
    def test_has_problematic_chars_excessive_special(self):
        """Test detection of excessive special characters."""
        excessive_special = "!@#$%^&*()!@#$%^&*()"  # All special chars
        assert ContentValidator._has_problematic_chars(excessive_special) is True
        
        normal_text = "Normal text with some punctuation!"
        assert ContentValidator._has_problematic_chars(normal_text) is False
    
    def test_sanitize_prompt(self):
        """Test prompt sanitization."""
        # Test whitespace cleanup
        messy_prompt = "  Generate   a    beautiful   sunset  "
        sanitized = ContentValidator.sanitize_prompt(messy_prompt)
        assert sanitized == "Generate a beautiful sunset"
        
        # Test control character removal
        text_with_control = "Normal text\x00with control"
        sanitized = ContentValidator.sanitize_prompt(text_with_control)
        assert "\x00" not in sanitized
        
        # Test consecutive punctuation limiting
        excessive_punct = "Amazing image!!!!!!"
        sanitized = ContentValidator.sanitize_prompt(excessive_punct)
        assert sanitized == "Amazing image!!"
    
    def test_validate_filename_valid(self):
        """Test valid filename passes validation."""
        is_valid, error_msg = ContentValidator.validate_filename("image.png")
        assert is_valid is True
        assert error_msg == ""
    
    def test_validate_filename_invalid_chars(self):
        """Test filename with invalid characters fails."""
        invalid_filenames = ["image<.png", "image>.png", "image:.png", "image/.png"]
        for filename in invalid_filenames:
            is_valid, error_msg = ContentValidator.validate_filename(filename)
            assert is_valid is False
            assert "invalid characters" in error_msg.lower()
    
    def test_validate_filename_reserved_names(self):
        """Test reserved filename fails validation."""
        reserved_names = ["CON.png", "PRN.jpg", "AUX.gif", "COM1.png"]
        for filename in reserved_names:
            is_valid, error_msg = ContentValidator.validate_filename(filename)
            assert is_valid is False
            assert "reserved name" in error_msg.lower()
    
    def test_validate_filename_too_long(self):
        """Test filename that's too long fails validation."""
        long_filename = "x" * 256  # Exceeds 255 character limit
        is_valid, error_msg = ContentValidator.validate_filename(long_filename)
        assert is_valid is False
        assert "too long" in error_msg.lower()
    
    def test_get_safe_filename(self):
        """Test safe filename generation."""
        # Test normal case
        safe_name = ContentValidator.get_safe_filename("my image", "png")
        assert safe_name == "my image.png"
        
        # Test with invalid characters
        unsafe_name = ContentValidator.get_safe_filename("my<image>", "png")
        assert "<" not in unsafe_name and ">" not in unsafe_name
        assert unsafe_name.endswith(".png")
        
        # Test empty name
        empty_safe = ContentValidator.get_safe_filename("", "png")
        assert empty_safe == "generated.png"
        
        # Test very long name
        long_name = "x" * 300
        safe_long = ContentValidator.get_safe_filename(long_name, "png")
        assert len(safe_long) < 255


class TestValidationFunctions:
    """Test cases for validation helper functions."""
    
    def test_validate_prompt_success(self):
        """Test validate_prompt function with valid input."""
        result = validate_prompt("Generate a beautiful sunset")
        assert result is True
    
    def test_validate_prompt_failure(self):
        """Test validate_prompt function with invalid input."""
        with pytest.raises(ValidationError):
            validate_prompt("")
        
        with pytest.raises(ValidationError):
            validate_prompt("x" * 1001)
    
    def test_validate_and_sanitize_prompt_success(self):
        """Test validate_and_sanitize_prompt with valid input."""
        messy_prompt = "  Generate   a    beautiful   sunset  "
        result = validate_and_sanitize_prompt(messy_prompt)
        assert result == "Generate a beautiful sunset"
    
    def test_validate_and_sanitize_prompt_failure(self):
        """Test validate_and_sanitize_prompt with invalid input."""
        with pytest.raises(ValidationError):
            validate_and_sanitize_prompt("")
        
        with pytest.raises(ValidationError):
            validate_and_sanitize_prompt("x" * 1001)


class TestValidatorInstance:
    """Test cases for the global validator instance."""
    
    def test_validator_instance_exists(self):
        """Test that global validator instance exists."""
        assert validator is not None
        assert isinstance(validator, ContentValidator)
    
    def test_validator_get_safe_filename(self):
        """Test validator instance methods work correctly."""
        filename = validator.get_safe_filename("test image", "png")
        assert filename == "test image.png"


# Edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_unicode_handling(self):
        """Test handling of unicode characters."""
        unicode_prompt = "Generate 🌅 sunset with 日本 mountains"
        is_valid, error_msg = ContentValidator.validate_prompt(unicode_prompt)
        assert is_valid is True  # Unicode should be allowed
    
    def test_mixed_language_prompt(self):
        """Test prompts with mixed languages."""
        mixed_prompt = "Generate una imagen beautiful"
        is_valid, error_msg = ContentValidator.validate_prompt(mixed_prompt)
        assert is_valid is True
    
    def test_numeric_only_prompt(self):
        """Test prompts that are only numbers."""
        numeric_prompt = "12345"
        is_valid, error_msg = ContentValidator.validate_prompt(numeric_prompt)
        assert is_valid is True
    
    def test_boundary_conditions(self):
        """Test various boundary conditions."""
        # Exactly at limits
        exactly_max = "x" * 1000
        assert ContentValidator.validate_prompt(exactly_max)[0] is True
        
        # Just over limit
        over_max = "x" * 1001
        assert ContentValidator.validate_prompt(over_max)[0] is False