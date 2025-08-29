# 🍌 BananaBot - AI Image Generation Discord Bot

A powerful Discord bot that uses Google's Gemini 2.5 Flash AI to generate and edit images through simple slash commands.

## ✨ Features

- **AI Image Generation** - Create stunning images from text descriptions
- **Image Editing** - Transform existing images with AI
- **URL Support** - Edit images directly from web URLs  
- **Personal Gallery** - Automatic saving of all your creations
- **Rate Limiting** - Fair usage for all users (10 requests/hour)
- **Slash Commands** - Modern Discord integration

## 🎯 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/generate` | Generate a new AI image from text | `/generate prompt: "sunset over mountains"` |
| `/generate-with-image` | Edit an attached image with AI | `/generate-with-image prompt: "make it purple" image: [file]` |
| `/generate-link` | Edit an image from a URL | `/generate-link prompt: "add a rainbow" image_url: "https://..."` |
| `/gallery` | View your recent creations | `/gallery limit: 5` |
| `/help` | Show available commands | `/help` |

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- Google Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/charlesinzesoussol/bananabot.git
cd bananabot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Configure your .env file**
```env
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

5. **Run the bot**
```bash
python start.py
```

## 📁 Project Structure

```
bananabot/
├── bot/                     # Core bot modules
│   ├── config.py           # Configuration settings
│   ├── models.py           # Data models (Gallery, Stats)
│   ├── services/           # External services
│   │   ├── gemini_client.py    # Gemini AI integration
│   │   └── batch_client_v2.py  # Batch processing
│   └── utils/              # Utilities
│       ├── rate_limiter.py     # Rate limiting
│       └── error_handler.py    # Error handling
├── user_galleries/         # User galleries (gitignored)
├── user_stats/            # User statistics (gitignored)
├── slash_bot.py           # Main bot with slash commands
├── start.py               # Bot launcher
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── .gitignore            # Git ignore rules
```

## ⚙️ Configuration

Edit `bot/config.py` to customize:

- `MAX_REQUESTS_PER_HOUR`: Rate limit per user (default: 10)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, WARNING, ERROR)
- `GEMINI_MODEL`: AI model to use (default: gemini-2.5-flash-image-preview)

## 🔒 Privacy & Security

- **User data is stored locally** and never shared
- **All user galleries are gitignored** for privacy
- **Environment variables** protect sensitive credentials
- **Rate limiting** prevents API abuse
- **Never commit** `.env` files or API keys

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes and test thoroughly
4. Commit your changes (`git commit -m 'Add AmazingFeature'`)
5. Push to the branch (`git push origin feature/AmazingFeature`)
6. Open a Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide
- Add type hints to functions
- Write clear commit messages
- Update documentation for new features
- Test your changes before submitting

## 🐛 Troubleshooting

### Bot not responding to commands?
- Ensure the bot has proper permissions in your Discord server
- Check that slash commands are synced (may take up to 1 hour globally)
- Verify the bot is online and shows as active

### Image generation failing?
- Verify your Gemini API key is valid and has quota
- Check the bot logs for specific error messages
- Ensure your prompt doesn't violate content policies

### Rate limit issues?
- Default is 10 requests per hour per user
- Adjust `MAX_REQUESTS_PER_HOUR` in config if needed
- Rate limits reset automatically

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Add to Discord**: [Invite BananaBot](https://discord.com/oauth2/authorize?client_id=1410744225120915498&permissions=274877910080&scope=bot%20applications.commands)
- **Report Issues**: [GitHub Issues](https://github.com/charlesinzesoussol/bananabot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/charlesinzesoussol/bananabot/discussions)

## 🙏 Acknowledgments

- [Discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [Google Gemini AI](https://deepmind.google/technologies/gemini/) - Image generation
- [Pydantic](https://pydantic.dev/) - Data validation
- The Discord community for feedback and support

---

⚠️ **Important**: This is a public repository. Never commit sensitive data like tokens, API keys, or user data. Always use environment variables for credentials.