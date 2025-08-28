name: "Discord Bot - Gemini 2.5 Flash Image Generation (nano-banana)"
description: |

## Purpose
Build a Discord bot that leverages Google's Gemini 2.5 Flash Image model (nano-banana) for AI image generation and editing. The bot provides slash commands for users to generate, edit, and manipulate images using natural language prompts.

## Core Principles
1. **Context is King**: Include ALL necessary Gemini API and Discord.py documentation
2. **Validation Loops**: Provide executable tests for Discord commands and API integration
3. **Information Dense**: Use patterns from both Discord.py 2.0+ and Google AI SDK
4. **Progressive Success**: Start with basic generation, validate, then add editing features
5. **Global rules**: Follow all rules in CLAUDE.md (no emojis, proper error handling)

---

## Goal
Build a production-ready Discord bot that generates images using Gemini 2.5 Flash Image model with:
- Slash command interface for image generation
- Support for image editing (inpainting, outpainting)
- Character consistency across multiple generations
- Rate limiting and error handling
- Asynchronous processing for scalability

## Why
- **Business value**: Provide Discord communities with AI-powered creative tools
- **User impact**: Enable users to generate custom images directly in Discord
- **Integration**: Leverage latest Gemini 2.5 Flash capabilities (nano-banana)
- **Problems solved**: Simplifies AI image generation for non-technical users

## What
Discord bot with slash commands that:
- `/generate` - Create images from text prompts
- `/edit` - Modify existing images with prompts
- `/compose` - Merge multiple images intelligently
- `/imagine` - Quick generation with preset styles

### Success Criteria
- [ ] Bot connects to Discord and registers slash commands
- [ ] Successfully generates images from text prompts
- [ ] Handles rate limiting gracefully
- [ ] Provides clear error messages
- [ ] Processes requests asynchronously
- [ ] Validates content for safety

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://ai.google.dev/gemini-api/docs/image-generation
  why: Official Gemini 2.5 Flash Image API documentation
  
- url: https://discordpy.readthedocs.io/en/stable/interactions/api.html
  why: Discord.py 2.0+ slash commands and interactions
  
- url: https://github.com/google-gemini/generative-ai-python
  why: Google AI Python SDK for Gemini
  
- doc: https://developers.googleblog.com/en/experiment-with-gemini-20-flash-native-image-generation/
  section: Model capabilities and limitations
  critical: Rate limits, content filtering, supported formats

- file: /Users/charles/Documents/projets_sulside/bananabot/CLAUDE.md
  why: Project-specific development rules and restrictions

- example: Discord.py 2.0+ slash command structure
  code: |
    import discord
    from discord import app_commands
    
    class MyBot(discord.Client):
        def __init__(self):
            intents = discord.Intents.default()
            super().__init__(intents=intents)
            self.tree = app_commands.CommandTree(self)
            
        async def setup_hook(self):
            await self.tree.sync()
    
    bot = MyBot()
    
    @bot.tree.command(name="generate", description="Generate an image")
    @app_commands.describe(prompt="Describe the image you want")
    async def generate(interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()  # For long operations
        # Process here
        await interaction.followup.send("Image generated!", file=file)

- example: Gemini 2.5 Flash Image generation
  code: |
    from google import genai
    from PIL import Image
    from io import BytesIO
    
    client = genai.Client(api_key="YOUR_API_KEY")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-image-preview",
        contents=[prompt, image],  # Can include existing image for editing
    )
    
    for part in response.parts:
        if image := part.as_image():
            image.save("generated.png")
```

### Current Codebase tree
```bash
bananabot/
├── CLAUDE.md
├── INITIAL.md
├── LICENSE
├── PRPs/
│   ├── EXAMPLE_multi_agent_prp.md
│   └── templates/
│       └── prp_base.md
├── README.md
└── examples/
```

### Desired Codebase tree with files to be added
```bash
bananabot/
├── bot/
│   ├── __init__.py
│   ├── main.py                  # Bot entry point and Discord client
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── generate.py          # /generate command implementation
│   │   ├── edit.py              # /edit command for image modification
│   │   └── compose.py           # /compose command for merging images
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_client.py     # Gemini API wrapper with retry logic
│   │   └── image_processor.py   # Image handling and validation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py        # Input validation and content filtering
│   │   ├── rate_limiter.py      # User-based rate limiting
│   │   └── error_handler.py     # Centralized error handling
│   └── config.py                # Configuration and environment variables
├── tests/
│   ├── __init__.py
│   ├── test_commands.py         # Discord command tests
│   ├── test_gemini_client.py    # API client tests
│   └── test_validators.py       # Validation tests
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Discord.py 2.0+ requires explicit tree syncing
# Bot won't see commands without await self.tree.sync()

# CRITICAL: Gemini API requires API key from AI Studio
# Get key at: https://aistudio.google.com/app/apikey

# CRITICAL: Discord file size limit is 8MB for regular servers
# Compress images if needed before sending

# CRITICAL: Gemini 2.5 Flash Image model name
# Use: "gemini-2.5-flash-image-preview" NOT "gemini-pro-vision"

# CRITICAL: Discord interactions timeout after 3 seconds
# Use defer() for long operations, then followup.send()

# CRITICAL: Rate limits
# Gemini API: Check quotas in AI Studio dashboard
# Discord API: 50 requests per second global limit

# CRITICAL: Async context - Discord.py is fully async
# All bot methods must be async def
```

## Implementation Blueprint

### Data models and structure

```python
# bot/models.py - Pydantic models for type safety
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    user_id: str
    guild_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('prompt')
    def validate_prompt(cls, v):
        # Check for inappropriate content
        banned_words = []  # Load from config
        if any(word in v.lower() for word in banned_words):
            raise ValueError("Inappropriate content detected")
        return v

class ImageEditRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    image_url: str
    edit_type: str = Field(default="inpaint")  # inpaint, outpaint, style
    user_id: str
    
class RateLimitInfo(BaseModel):
    user_id: str
    requests_count: int = 0
    window_start: datetime
    max_requests: int = 10  # Per hour
```

### List of tasks to be completed in order

```yaml
Task 1: Setup project structure and dependencies
CREATE requirements.txt:
  - discord.py>=2.3.0
  - google-generativeai>=0.8.0
  - python-dotenv>=1.0.0
  - aiohttp>=3.9.0
  - Pillow>=10.0.0
  - pydantic>=2.0.0
  - pytest>=7.4.0
  - pytest-asyncio>=0.21.0

CREATE .env.example:
  - DISCORD_TOKEN=your_bot_token_here
  - GEMINI_API_KEY=your_gemini_api_key_here
  - GUILD_ID=your_test_guild_id  # Optional for testing

Task 2: Implement configuration management
CREATE bot/config.py:
  - Load environment variables with python-dotenv
  - Define configuration constants
  - Validate required environment variables exist

Task 3: Create Gemini API client wrapper
CREATE bot/services/gemini_client.py:
  - Initialize google.genai.Client with API key
  - Implement generate_image() with retry logic
  - Implement edit_image() for modifications
  - Add error handling for API failures
  - Add content safety checks

Task 4: Implement Discord bot core
CREATE bot/main.py:
  - Define BananaBot class extending discord.Client
  - Setup intents and command tree
  - Implement setup_hook() for command syncing
  - Add on_ready() event handler
  - Configure logging

Task 5: Create rate limiting utility
CREATE bot/utils/rate_limiter.py:
  - Implement per-user rate limiting
  - Use asyncio locks for thread safety
  - Track requests in memory (or Redis for production)
  - Return clear messages when limit exceeded

Task 6: Implement /generate command
CREATE bot/commands/generate.py:
  - Define slash command with app_commands.command
  - Add prompt parameter with description
  - Defer interaction for long processing
  - Call Gemini API through service
  - Convert response to Discord file
  - Send followup with generated image

Task 7: Implement /edit command
CREATE bot/commands/edit.py:
  - Accept image attachment and prompt
  - Validate image format and size
  - Process edit through Gemini API
  - Return modified image

Task 8: Add input validators
CREATE bot/utils/validators.py:
  - Validate prompt length and content
  - Check image formats (PNG, JPG, etc.)
  - Implement content filtering
  - Validate file sizes

Task 9: Implement error handling
CREATE bot/utils/error_handler.py:
  - Create custom exception classes
  - Implement global error handler
  - Format user-friendly error messages
  - Log errors for debugging

Task 10: Create comprehensive tests
CREATE tests/test_commands.py:
  - Mock Discord interactions
  - Test command parameter validation
  - Test error scenarios

CREATE tests/test_gemini_client.py:
  - Mock Gemini API responses
  - Test retry logic
  - Test error handling

Task 11: Add Docker support
CREATE Dockerfile:
  - Use Python 3.11+ base image
  - Install dependencies
  - Configure for production

Task 12: Update documentation
UPDATE README.md:
  - Installation instructions
  - Bot setup guide
  - Command documentation
  - Deployment instructions
```

### Per task pseudocode

```python
# Task 3: Gemini Client Implementation
# bot/services/gemini_client.py
import asyncio
from typing import Optional
from google import genai
from PIL import Image
import io

class GeminiImageClient:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash-image-preview"
        
    async def generate_image(self, prompt: str, retry_count: int = 3) -> bytes:
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
                return response
            except Exception as e:
                if attempt == retry_count - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _generate_sync(self, prompt: str) -> bytes:
        # GOTCHA: Gemini expects list format for contents
        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
        )
        
        # PATTERN: Extract image from response parts
        for part in response.parts:
            if image := part.as_image():
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue()
        
        raise ValueError("No image generated")

# Task 6: Generate Command Implementation
# bot/commands/generate.py
import discord
from discord import app_commands
from typing import Optional

class GenerateCommand:
    def __init__(self, bot, gemini_client, rate_limiter):
        self.bot = bot
        self.gemini = gemini_client
        self.rate_limiter = rate_limiter
        
    def setup(self):
        @self.bot.tree.command(name="generate", description="Generate an AI image")
        @app_commands.describe(
            prompt="Describe the image you want to generate",
            style="Optional style modifier"
        )
        async def generate(
            interaction: discord.Interaction, 
            prompt: str,
            style: Optional[str] = None
        ):
            # PATTERN: Defer for long operations (>3 seconds)
            await interaction.response.defer(thinking=True)
            
            # PATTERN: Rate limiting check
            if not await self.rate_limiter.check_user(str(interaction.user.id)):
                await interaction.followup.send(
                    "Rate limit exceeded. Please try again later.",
                    ephemeral=True
                )
                return
            
            try:
                # CRITICAL: Validate input first
                if len(prompt) > 1000:
                    raise ValueError("Prompt too long (max 1000 characters)")
                
                # Enhance prompt with style if provided
                full_prompt = f"{prompt}, {style} style" if style else prompt
                
                # Generate image
                image_bytes = await self.gemini.generate_image(full_prompt)
                
                # PATTERN: Convert to Discord file
                file = discord.File(
                    io.BytesIO(image_bytes),
                    filename="generated.png"
                )
                
                # Send response
                await interaction.followup.send(
                    f"Generated image for: {prompt[:100]}...",
                    file=file
                )
                
            except Exception as e:
                # PATTERN: User-friendly error messages
                await interaction.followup.send(
                    "Failed to generate image. Please try again.",
                    ephemeral=True
                )
                # Log full error for debugging
                print(f"Generation error: {e}")
```

### Integration Points
```yaml
ENVIRONMENT:
  - file: .env
  - vars:
    - DISCORD_TOKEN: Bot token from Discord Developer Portal
    - GEMINI_API_KEY: API key from Google AI Studio
    - LOG_LEVEL: INFO/DEBUG/ERROR
    - MAX_REQUESTS_PER_HOUR: 10
  
DISCORD:
  - permissions: Send Messages, Attach Files, Use Slash Commands
  - intents: default (no message content needed for slash commands)
  - oauth2: applications.commands scope required
  
GEMINI_API:
  - endpoint: https://generativelanguage.googleapis.com
  - model: gemini-2.5-flash-image-preview
  - quotas: Check AI Studio dashboard
  - billing: Enable if exceeding free tier
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Create virtual environment
python -m venv venv_linux
source venv_linux/bin/activate  # Linux/Mac
# or
venv_linux\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run linting and type checking
ruff check bot/ --fix
mypy bot/ --ignore-missing-imports

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# tests/test_gemini_client.py
import pytest
from unittest.mock import Mock, patch
from bot.services.gemini_client import GeminiImageClient

@pytest.mark.asyncio
async def test_generate_image_success():
    """Test successful image generation"""
    client = GeminiImageClient("fake_key")
    
    with patch.object(client, '_generate_sync') as mock_gen:
        mock_gen.return_value = b"fake_image_data"
        
        result = await client.generate_image("test prompt")
        assert result == b"fake_image_data"
        mock_gen.assert_called_once_with("test prompt")

@pytest.mark.asyncio
async def test_generate_image_retry():
    """Test retry logic on failure"""
    client = GeminiImageClient("fake_key")
    
    with patch.object(client, '_generate_sync') as mock_gen:
        mock_gen.side_effect = [Exception("API Error"), b"success"]
        
        result = await client.generate_image("test", retry_count=2)
        assert result == b"success"
        assert mock_gen.call_count == 2

# tests/test_validators.py
import pytest
from bot.utils.validators import validate_prompt

def test_validate_prompt_valid():
    """Test valid prompt passes validation"""
    assert validate_prompt("Generate a sunset") == True

def test_validate_prompt_too_long():
    """Test prompt length limit"""
    long_prompt = "x" * 1001
    with pytest.raises(ValueError, match="too long"):
        validate_prompt(long_prompt)

def test_validate_prompt_inappropriate():
    """Test content filtering"""
    # Add actual banned words in production
    assert validate_prompt("normal prompt") == True
```

```bash
# Run tests
pytest tests/ -v --asyncio-mode=auto

# Expected: All tests pass
# If failing: Debug specific test, fix implementation
```

### Level 3: Integration Test
```bash
# Start the bot in test mode
python -m bot.main --test

# In another terminal, test with Discord
# Or use discord.py test client:
```

```python
# tests/test_integration.py
import discord
from discord.ext import commands
import pytest

@pytest.mark.asyncio
async def test_bot_connects():
    """Test bot connects to Discord"""
    # Create test bot instance
    bot = create_test_bot()
    
    # Test connection
    await bot.start(test_token)
    assert bot.is_ready()
    
    # Test command registration
    commands = [cmd.name for cmd in bot.tree.get_commands()]
    assert "generate" in commands
    assert "edit" in commands
    
    await bot.close()
```

### Level 4: Manual Testing
```bash
# 1. Invite bot to test server
# Use OAuth2 URL with applications.commands scope

# 2. Test commands in Discord
/generate prompt:"A serene mountain landscape at sunset"
/generate prompt:"Cyberpunk city" style:"neon noir"
/edit prompt:"Add a rainbow" [attach image]

# 3. Test error cases
/generate prompt:"" # Empty prompt
/generate prompt:[1001 characters] # Too long

# 4. Test rate limiting
# Send 11 requests rapidly, 11th should be rate limited

# Expected responses:
# - Images generated successfully
# - Clear error messages for failures
# - Rate limit message after threshold
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check bot/`
- [ ] No type errors: `mypy bot/`
- [ ] Bot connects to Discord
- [ ] Slash commands appear in Discord
- [ ] Images generate successfully
- [ ] Rate limiting works correctly
- [ ] Error messages are user-friendly
- [ ] Logs are informative but not verbose
- [ ] README updated with setup instructions
- [ ] .env.example includes all required variables
- [ ] No API keys in code or commits

---

## Anti-Patterns to Avoid
- ❌ Don't hardcode API keys or tokens
- ❌ Don't use synchronous operations in async context
- ❌ Don't ignore Discord interaction timeouts (3 seconds)
- ❌ Don't send files larger than 8MB to Discord
- ❌ Don't skip input validation
- ❌ Don't expose technical errors to users
- ❌ Don't forget to defer long operations
- ❌ Don't use blocking I/O without run_in_executor
- ❌ Don't ignore rate limits (both Discord and Gemini)
- ❌ Don't forget to sync command tree

## Confidence Score: 9/10

This PRP provides comprehensive context for implementing a Discord bot with Gemini 2.5 Flash Image generation. The score is 9/10 because:
- ✅ Complete implementation blueprint with all files
- ✅ Detailed pseudocode for critical components
- ✅ Library-specific gotchas documented
- ✅ Executable validation gates
- ✅ Clear task ordering
- ✅ Error handling patterns included
- ✅ Rate limiting implementation
- ✅ Test coverage defined
- ⚠️ Minor: Gemini API specifics may need adjustment based on latest docs