# 🍌 BananaBot

Discord AI image generation bot using Google Gemini 2.5 Flash with multi-image fusion capabilities.

## Commands

- `/generate <prompt>` - Generate AI image from text
- `/generate-with-image <prompt> <image>` - Edit uploaded image  
- `/generate-link <prompt> <url>` - Edit image from URL
- `/fuse-images <prompt> <img1> <img2> [img3-5]` - **NEW:** Combine multiple images creatively
- `/gallery [limit]` - View your creations  
- `/help` - Show commands

## Multi-Image Fusion

The `/fuse-images` command leverages Gemini 2.5 Flash's advanced capabilities to combine 2-5 images:

**Use Cases:**
- Product placement in scenes
- Room restyling with color schemes/textures  
- Creative image combinations
- Merging visual elements from different sources

**Example:**
```
/fuse-images prompt:"Place this product in a modern living room" image1:[product.jpg] image2:[room.jpg]
```

**Security:**
- Same rate limiting (3 requests/hour/user)
- File validation and size limits (8MB per image)
- Cost tracking and user gallery integration

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Create `.env` from `.env.example`
3. Add your tokens to `.env`
4. Run: `python start.py`

## Production Features

**Cost Management:**
- Rate limiting: 3 requests/hour/user (max $2.81/day/user)
- Batch processing with 50% cost savings
- Real-time cost tracking and projections
- Growth monitoring: `./check` for metrics

**Security:**
- Industry-standard configuration validation  
- Atomic file operations prevent data corruption
- Rate limiter with race condition protection
- Content filtering and input sanitization
- Environment variable security

**Monitoring:**
- Local metrics: `./check` or `python3 show_metrics.py`
- User gallery and statistics persistence
- Comprehensive error logging

## VPS Deployment

Automatic zero-downtime deployment via GitHub Actions. Every push to main deploys to VPS with:
- Service restart with minimal downtime
- Environment configuration updates
- Dependency management
- Data directory initialization

## Requirements

- Python 3.9+
- Discord Bot Token
- Google Gemini API Key

## License

MIT