# 🍌 BananaBot

Discord AI image generation bot using Google Gemini 2.5 Flash.

## Commands

- `/generate <prompt>` - Generate AI image from text
- `/generate-with-image <prompt> <image>` - Edit uploaded image  
- `/generate-link <prompt> <url>` - Edit image from URL
- `/gallery` - View your creations
- `/help` - Show commands

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` from `.env.example`
3. Add your tokens to `.env`
4. Run: `python start.py`

## VPS Deployment

Automatic deployment via GitHub Actions. Every push to main deploys to VPS.

## Requirements

- Python 3.9+
- Discord Bot Token
- Google Gemini API Key

## License

MIT