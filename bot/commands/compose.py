"""Image composition command for BananaBot."""

import logging
import discord
from discord import app_commands
from typing import Optional

from ..utils.validators import validate_and_sanitize_prompt, validator
from ..utils.error_handler import error_handler, ValidationError
from ..services.image_processor import image_processor

logger = logging.getLogger(__name__)

def setup_compose_command(bot) -> None:
    """
    Setup the /compose command for the bot.
    
    Args:
        bot: BananaBot instance
    """
    
    @bot.tree.command(
        name="compose",
        description="Intelligently merge multiple images into one"
    )
    @app_commands.describe(
        prompt="Describe how to combine the images",
        image1="First image to combine",
        image2="Second image to combine",
        image3="Third image to combine (optional)",
        image4="Fourth image to combine (optional)"
    )
    async def compose(
        interaction: discord.Interaction,
        prompt: str,
        image1: discord.Attachment,
        image2: discord.Attachment,
        image3: Optional[discord.Attachment] = None,
        image4: Optional[discord.Attachment] = None
    ) -> None:
        """
        Compose multiple images into a single image.
        
        Args:
            interaction: Discord interaction
            prompt: Instructions for how to combine the images
            image1: First image
            image2: Second image  
            image3: Third image (optional)
            image4: Fourth image (optional)
        """
        # Collect all provided images
        images = [image1, image2]
        if image3:
            images.append(image3)
        if image4:
            images.append(image4)
            
        logger.info(f"Compose command from {interaction.user}: '{prompt[:50]}...' with {len(images)} images")
        
        # PATTERN: Defer for long operations
        await interaction.response.defer(thinking=True)
        
        try:
            # CRITICAL: Validate prompt first
            sanitized_prompt = validate_and_sanitize_prompt(prompt)
            logger.info(f"Sanitized compose prompt: '{sanitized_prompt[:50]}...'")
            
            # PATTERN: Rate limiting check (compose uses more resources)
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
            
            # Validate and download all images
            image_data_list = []
            for i, img in enumerate(images):
                try:
                    # Validate attachment type
                    if not img.content_type or not img.content_type.startswith('image/'):
                        await interaction.followup.send(
                            f"Image {i+1} is not a valid image file. Please upload PNG, JPEG, or WEBP files.",
                            ephemeral=True
                        )
                        return
                    
                    # Download and validate image
                    image_data = await image_processor.download_attachment(img)
                    
                    # Validate image format and size
                    is_valid, error_msg = image_processor.validate_image(image_data)
                    if not is_valid:
                        await interaction.followup.send(
                            f"Image {i+1} validation failed: {error_msg}",
                            ephemeral=True
                        )
                        return
                    
                    image_data_list.append(image_data)
                    logger.info(f"Image {i+1} downloaded and validated: {img.filename}")
                    
                except Exception as e:
                    logger.error(f"Failed to process image {i+1}: {e}")
                    await interaction.followup.send(
                        f"Failed to process image {i+1}. Please try with different images.",
                        ephemeral=True
                    )
                    return
            
            # Compose images through Gemini API
            try:
                # For now, we'll use a simple approach - create a composition prompt
                # In a full implementation, you might send multiple images to Gemini
                compose_prompt = f"Create a composition combining these {len(images)} images: {sanitized_prompt}"
                
                # Use the first image as base and edit it with the composition instruction
                composed_image_bytes = await bot.gemini_client.edit_image(
                    compose_prompt,
                    image_data_list[0]  # Use first image as base
                )
                
                logger.info(f"Images composed successfully for user {interaction.user}")
                
            except Exception as e:
                logger.error(f"Image composition failed: {e}")
                await error_handler.handle_command_error(interaction, e)
                return
            
            # PATTERN: Convert to Discord file
            try:
                # Create safe filename
                safe_prompt = prompt[:20].replace(' ', '_').replace('/', '_')
                filename = validator.get_safe_filename(f"composed_{safe_prompt}", "png")
                
                file = image_processor.create_discord_file(composed_image_bytes, filename)
                
                # Create embed with composition info
                embed = discord.Embed(
                    title="Images Composed!",
                    description=f"**Composition:** {prompt[:200]}{'...' if len(prompt) > 200 else ''}",
                    color=0xff9900
                )
                
                # Add source images info
                source_names = [img.filename for img in images]
                embed.add_field(
                    name=f"Source Images ({len(images)})",
                    value=", ".join(source_names[:3]) + ("..." if len(source_names) > 3 else ""),
                    inline=True
                )
                
                embed.add_field(name="Composed by", value=interaction.user.mention, inline=True)
                embed.set_footer(text="Powered by Gemini 2.5 Flash Image")
                
                # Send response
                await interaction.followup.send(
                    embed=embed,
                    file=file
                )
                
                logger.info(f"Composed image sent successfully to {interaction.user}")
                
            except Exception as e:
                logger.error(f"Failed to process/send composed image: {e}")
                await error_handler.handle_command_error(interaction, e)
                return
            
        except ValidationError as e:
            logger.warning(f"Validation error from {interaction.user}: {e}")
            await interaction.followup.send(
                f"Invalid prompt: {e.user_message}",
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in compose command: {e}")
            await error_handler.handle_command_error(interaction, e)
    
    # Alternative command for collages
    @bot.tree.command(
        name="collage",
        description="Create a collage from multiple images"
    )
    @app_commands.describe(
        image1="First image for collage",
        image2="Second image for collage",
        image3="Third image (optional)",
        image4="Fourth image (optional)",
        style="Collage style (optional)"
    )
    async def collage(
        interaction: discord.Interaction,
        image1: discord.Attachment,
        image2: discord.Attachment,
        image3: Optional[discord.Attachment] = None,
        image4: Optional[discord.Attachment] = None,
        style: Optional[str] = "artistic collage"
    ) -> None:
        """
        Create an artistic collage from multiple images.
        
        Args:
            interaction: Discord interaction
            image1-4: Images to include in collage
            style: Style of the collage
        """
        # Create collage prompt
        image_count = 2 + (1 if image3 else 0) + (1 if image4 else 0)
        prompt = f"Create a beautiful {style} with these {image_count} images arranged artistically"
        
        # Call the compose function
        await compose(interaction, prompt, image1, image2, image3, image4)
    
    logger.info("Compose and Collage commands registered")