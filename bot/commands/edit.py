"""Image editing command for BananaBot."""

import logging
import discord
from discord import app_commands
from typing import Optional

from ..utils.validators import validate_and_sanitize_prompt, validator
from ..utils.error_handler import error_handler, ValidationError
from ..services.image_processor import image_processor

logger = logging.getLogger(__name__)

def setup_edit_command(bot) -> None:
    """
    Setup the /edit command for the bot.
    
    Args:
        bot: BananaBot instance
    """
    
    @bot.tree.command(
        name="edit",
        description="Edit an existing image using AI"
    )
    @app_commands.describe(
        prompt="Describe how you want to edit the image",
        image="Upload the image you want to edit"
    )
    async def edit(
        interaction: discord.Interaction,
        prompt: str,
        image: discord.Attachment
    ) -> None:
        """
        Edit an existing image based on a text prompt.
        
        Args:
            interaction: Discord interaction
            prompt: Text description of the desired edit
            image: Image attachment to edit
        """
        logger.info(f"Edit command from {interaction.user}: '{prompt[:50]}...' on {image.filename}")
        
        # PATTERN: Defer for long operations
        await interaction.response.defer(thinking=True)
        
        try:
            # CRITICAL: Validate prompt first
            sanitized_prompt = validate_and_sanitize_prompt(prompt)
            logger.info(f"Sanitized edit prompt: '{sanitized_prompt[:50]}...'")
            
            # PATTERN: Rate limiting check
            user_id = str(interaction.user.id)
            if not await bot.rate_limiter.check_user(user_id):
                status = await bot.rate_limiter.get_user_status(user_id)
                reset_time = status.get('reset_time')
                
                if reset_time:
                    minutes = int(reset_time // 60)
                    message = f"Rate limit exceeded. Try again in {minutes} minutes."
                else:
                    message = "Rate limit exceeded. Please try again later."
                
                await interaction.followup.send(message, ephemeral=True)
                return
            
            # Validate image attachment
            if not image.content_type or not image.content_type.startswith('image/'):
                await interaction.followup.send(
                    "Please upload a valid image file (PNG, JPEG, WEBP).",
                    ephemeral=True
                )
                return
            
            # Download and validate image
            try:
                image_data = await image_processor.download_attachment(image)
                
                # Validate image format and size
                is_valid, error_msg = image_processor.validate_image(image_data)
                if not is_valid:
                    await interaction.followup.send(
                        f"Image validation failed: {error_msg}",
                        ephemeral=True
                    )
                    return
                
                logger.info(f"Image downloaded and validated: {image.filename}")
                
            except Exception as e:
                logger.error(f"Failed to download/validate image: {e}")
                await interaction.followup.send(
                    "Failed to process the uploaded image. Please try with a different image.",
                    ephemeral=True
                )
                return
            
            # Edit image through Gemini API
            try:
                edited_image_bytes = await bot.gemini_client.edit_image(
                    sanitized_prompt,
                    image_data
                )
                logger.info(f"Image edited successfully for user {interaction.user}")
                
            except Exception as e:
                logger.error(f"Image editing failed: {e}")
                await error_handler.handle_command_error(interaction, e)
                return
            
            # PATTERN: Convert to Discord file
            try:
                # Create safe filename
                original_name = image.filename.split('.')[0] if '.' in image.filename else image.filename
                safe_prompt = prompt[:20].replace(' ', '_').replace('/', '_')
                filename = validator.get_safe_filename(f"edited_{original_name}_{safe_prompt}", "png")
                
                file = image_processor.create_discord_file(edited_image_bytes, filename)
                
                # Create embed with edit info
                embed = discord.Embed(
                    title="Image Edited!",
                    description=f"**Edit:** {prompt[:200]}{'...' if len(prompt) > 200 else ''}",
                    color=0x0099ff
                )
                
                embed.add_field(name="Original Image", value=image.filename, inline=True)
                embed.add_field(name="Edited by", value=interaction.user.mention, inline=True)
                embed.set_footer(text="Powered by Gemini 2.5 Flash Image")
                
                # Send response
                await interaction.followup.send(
                    embed=embed,
                    file=file
                )
                
                logger.info(f"Edited image sent successfully to {interaction.user}")
                
            except Exception as e:
                logger.error(f"Failed to process/send edited image: {e}")
                await error_handler.handle_command_error(interaction, e)
                return
            
        except ValidationError as e:
            logger.warning(f"Validation error from {interaction.user}: {e}")
            await interaction.followup.send(
                f"Invalid prompt: {e.user_message}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in edit command: {e}")
            await error_handler.handle_command_error(interaction, e)
    
    # Additional command for inpainting specifically
    @bot.tree.command(
        name="inpaint",
        description="Remove or replace objects in an image"
    )
    @app_commands.describe(
        image="Upload the image to edit",
        remove="Describe what to remove from the image",
        add="Describe what to add to the image (optional)"
    )
    async def inpaint(
        interaction: discord.Interaction,
        image: discord.Attachment,
        remove: str,
        add: Optional[str] = None
    ) -> None:
        """
        Specialized inpainting command for removing/replacing objects.
        
        Args:
            interaction: Discord interaction
            image: Image to edit
            remove: What to remove
            add: What to add (optional)
        """
        # Construct edit prompt
        if add:
            prompt = f"Remove {remove} and add {add}"
        else:
            prompt = f"Remove {remove}"
        
        # Call the edit function
        await edit(interaction, prompt, image)
    
    logger.info("Edit and Inpaint commands registered")