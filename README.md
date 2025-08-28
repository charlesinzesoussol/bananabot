# BananaBot - Discord Image Generation Bot

A Discord bot that generates and edits images using Google's Gemini 2.5 Flash Image model (nano-banana). Create stunning AI-generated images directly in your Discord server with simple slash commands.

![BananaBot Demo](https://via.placeholder.com/800x400/FFE135/000000?text=BananaBot+Discord+Image+Generator)

## Features

- **Image Generation**: Create images from text prompts using `/generate`
- **Image Editing**: Modify existing images with AI using `/edit` and `/inpaint`
- **Image Composition**: Merge multiple images artistically with `/compose` and `/collage`
- **Preset Styles**: Quick generation with preset styles using `/imagine`
- **Rate Limiting**: Built-in user rate limiting to manage API usage
- **Content Filtering**: Safety checks for appropriate content
- **Error Handling**: Robust error handling with user-friendly messages

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bananabot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens
   ```

4. **Run the bot**
   ```bash
   python -m bot.main
   ```

### Docker Installation

```bash
# Build the image
docker build -t bananabot .

# Run with environment file
docker run --env-file .env bananabot

# Or with environment variables
docker run -e DISCORD_TOKEN=your_token -e GEMINI_API_KEY=your_key bananabot
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Required
DISCORD_TOKEN=your_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
GUILD_ID=your_test_guild_id           # For testing (faster sync)
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR
MAX_REQUESTS_PER_HOUR=10             # Rate limit per user
ENABLE_CONTENT_FILTER=true           # Enable content filtering
```

## Bot Setup

### 1. Create Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Copy the bot token for your `.env` file
5. Enable required intents (no special intents needed for slash commands)

### 2. Get Bot Permissions

The bot needs these permissions:
- Send Messages
- Attach Files
- Use Slash Commands

OAuth2 URL Generator will create an invite link with correct permissions.

### 3. Get Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key for your `.env` file
4. Ensure you have access to Gemini 2.5 Flash Image model

### 4. Invite Bot to Server

Use the OAuth2 URL from Discord Developer Portal to invite your bot to a server.

## Commands

### `/generate`
Generate images from text descriptions.

```
/generate prompt: "A serene mountain landscape at sunset"
/generate prompt: "Cyberpunk city street" style: "neon noir"
```

**Parameters:**
- `prompt` (required): Description of the image to generate (max 1000 chars)
- `style` (optional): Style modifier for the image

### `/imagine`
Quick generation with preset styles.

```
/imagine prompt: "A cat in space" style: "Photorealistic"
```

**Available styles:**
- Photorealistic
- Digital Art
- Oil Painting
- Watercolor
- Cartoon
- Anime
- Cyberpunk
- Fantasy

### `/edit`
Edit existing images with AI.

```
/edit prompt: "Add a rainbow to the sky" image: [upload image]
```

**Parameters:**
- `prompt` (required): Description of how to edit the image
- `image` (required): Image file to edit (PNG, JPEG, WEBP)

### `/inpaint`
Remove or replace objects in images.

```
/inpaint image: [upload] remove: "car" add: "bicycle"
/inpaint image: [upload] remove: "background" 
```

**Parameters:**
- `image` (required): Image to edit
- `remove` (required): What to remove from the image
- `add` (optional): What to add to the image

### `/compose`
Merge multiple images intelligently.

```
/compose prompt: "Create artistic collage" image1: [upload] image2: [upload]
```

**Parameters:**
- `prompt` (required): How to combine the images
- `image1-4`: 2-4 images to compose (at least 2 required)

### `/collage`
Create artistic collages from multiple images.

```
/collage image1: [upload] image2: [upload] style: "vintage"
```

## Rate Limits

- **Default**: 10 requests per user per hour
- **Configurable**: Set `MAX_REQUESTS_PER_HOUR` in environment
- **Per-user**: Each user has their own limit
- **Reset**: Automatically resets after the time window

## File Limits

- **Image Size**: 8MB maximum (Discord limit)
- **Supported Formats**: PNG, JPEG, JPG, WEBP
- **Auto-optimization**: Large images are automatically compressed

## Development

### Project Structure

```
bananabot/
├── bot/
│   ├── main.py              # Bot entry point
│   ├── config.py            # Configuration management
│   ├── commands/            # Discord slash commands
│   │   ├── generate.py      # /generate and /imagine commands
│   │   ├── edit.py          # /edit and /inpaint commands
│   │   └── compose.py       # /compose and /collage commands
│   ├── services/            # External service integrations
│   │   ├── gemini_client.py # Gemini API wrapper
│   │   └── image_processor.py # Image handling utilities
│   └── utils/               # Utility modules
│       ├── validators.py    # Input validation
│       ├── rate_limiter.py  # Rate limiting logic
│       └── error_handler.py # Error handling
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
└── .env.example           # Environment template
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=bot

# Run specific test file
pytest tests/test_commands.py -v
```

### Code Quality

```bash
# Linting
ruff check bot/ --fix

# Type checking
mypy bot/ --ignore-missing-imports

# Format code
black bot/ tests/
```

### Development Mode

For faster testing, set a specific guild ID:

```env
GUILD_ID=your_server_id
```

This syncs commands only to that server (appears instantly vs. up to 1 hour globally).

## Deployment

### Docker Deployment

```bash
# Build production image
docker build -t bananabot:latest .

# Run with restart policy
docker run -d \
  --name bananabot \
  --restart unless-stopped \
  --env-file .env \
  bananabot:latest
```

### Environment Considerations

**Production:**
- Remove `GUILD_ID` for global command sync
- Set `LOG_LEVEL=WARNING` or `ERROR`
- Monitor API usage and costs
- Set appropriate `MAX_REQUESTS_PER_HOUR`

**Security:**
- Never commit API keys to version control
- Use environment variables or secrets management
- Run container as non-root user (handled in Dockerfile)

## API Usage & Costs

### Gemini API Limits

- **Free tier**: Limited requests per month
- **Paid tier**: Higher limits based on billing
- **Rate limits**: Check Google AI Studio dashboard

### Cost Optimization

- Enable rate limiting to control usage
- Monitor API calls in Google Cloud Console
- Set billing alerts
- Use content filtering to prevent wasted generations

## Troubleshooting

### Common Issues

**Bot not responding to commands:**
1. Check bot has correct permissions in Discord
2. Verify commands are synced (`setup_hook` logs)
3. Ensure bot is online and connected

**Image generation fails:**
1. Verify Gemini API key is valid
2. Check API quotas in Google AI Studio
3. Ensure prompt passes content filters

**Rate limit issues:**
1. Adjust `MAX_REQUESTS_PER_HOUR` in config
2. Check rate limiter logs
3. Verify per-user tracking is working

**Image too large errors:**
1. Images auto-compress, but may still exceed limits
2. Try smaller input images
3. Check Discord server boost level (affects limits)

### Logs

Bot logs to both console and `bananabot.log` file:

```bash
# View recent logs
tail -f bananabot.log

# Search for errors
grep ERROR bananabot.log
```

### Health Checks

The bot includes health check endpoints and monitoring:

```python
# Check Gemini API health
await bot.gemini_client.health_check()

# Check rate limiter status
await bot.rate_limiter.get_user_status(user_id)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Write tests for new features
- Update documentation for changes
- Ensure all tests pass before submitting

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI image generation
- [Pillow](https://python-pillow.org/) - Image processing
- [Pydantic](https://pydantic.dev/) - Data validation

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/bananabot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/bananabot/discussions)
- **Discord**: Join our support server [Discord Invite](https://discord.gg/your-invite)

---

**Powered by Gemini 2.5 Flash Image (nano-banana) 🍌**