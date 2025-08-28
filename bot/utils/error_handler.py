"""Centralized error handling for BananaBot."""

import logging
import traceback
from typing import Optional
import discord
from discord import app_commands

logger = logging.getLogger(__name__)

class BananaBotError(Exception):
    """Base exception for BananaBot errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        """
        Initialize error.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message to display
        """
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An error occurred while processing your request."

class GeminiAPIError(BananaBotError):
    """Gemini API related errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            user_message or "Failed to generate image. Please try again later."
        )

class ContentFilterError(BananaBotError):
    """Content filter related errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            user_message or "Your request was blocked by content filters. Please try a different prompt."
        )

class RateLimitError(BananaBotError):
    """Rate limiting related errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            user_message or "Rate limit exceeded. Please wait before making another request."
        )

class ValidationError(BananaBotError):
    """Input validation related errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            user_message or "Invalid input provided. Please check your request and try again."
        )

class ImageProcessingError(BananaBotError):
    """Image processing related errors."""
    
    def __init__(self, message: str, user_message: Optional[str] = None):
        super().__init__(
            message,
            user_message or "Failed to process image. Please check the format and try again."
        )

class ErrorHandler:
    """Centralized error handler for Discord commands."""
    
    @staticmethod
    async def handle_command_error(
        interaction: discord.Interaction,
        error: Exception,
        ephemeral: bool = True
    ) -> None:
        """
        Handle errors in Discord slash commands.
        
        Args:
            interaction: Discord interaction
            error: Exception that occurred
            ephemeral: Whether to send ephemeral response
        """
        logger.error(f"Command error in {interaction.command}: {error}")
        logger.error(traceback.format_exc())
        
        # Determine user message
        if isinstance(error, BananaBotError):
            user_message = error.user_message
        elif isinstance(error, app_commands.CommandInvokeError):
            # Unwrap the original error
            original_error = error.original
            if isinstance(original_error, BananaBotError):
                user_message = original_error.user_message
            else:
                user_message = "An unexpected error occurred. Please try again."
        else:
            user_message = "An unexpected error occurred. Please try again."
        
        try:
            # Send error response
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"Error: {user_message}",
                    ephemeral=ephemeral
                )
            else:
                await interaction.response.send_message(
                    f"Error: {user_message}",
                    ephemeral=ephemeral
                )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")
    
    @staticmethod
    def log_error(error: Exception, context: str = "") -> None:
        """
        Log error with context.
        
        Args:
            error: Exception to log
            context: Additional context information
        """
        context_str = f" in {context}" if context else ""
        logger.error(f"Error{context_str}: {error}")
        logger.error(traceback.format_exc())
    
    @staticmethod
    async def handle_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        """
        Global error handler for command tree.
        
        Args:
            interaction: Discord interaction
            error: App command error
        """
        logger.error(f"Tree error: {error}")
        
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(
                "I don't have the required permissions to execute this command.",
                ephemeral=True
            )
        else:
            await ErrorHandler.handle_command_error(interaction, error)

# Global error handler instance
error_handler = ErrorHandler()