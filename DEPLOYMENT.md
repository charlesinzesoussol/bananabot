# 🚀 BananaBot VPS Deployment Guide

This guide explains how to deploy BananaBot to your VPS at `178.156.195.131`.

## Prerequisites

- VPS with Ubuntu/Debian
- SSH access to your VPS
- GitHub repository secrets configured
- Python 3.9+ installed on VPS

## Initial VPS Setup

### 1. Connect to your VPS
```bash
ssh root@178.156.195.131
```

### 2. Run the setup script
```bash
# Download and run setup script
wget https://raw.githubusercontent.com/charlesinzesoussol/bananabot/main/scripts/vps-setup.sh
chmod +x vps-setup.sh
./vps-setup.sh
```

### 3. Create .env file
```bash
cd ~/bananabot
nano .env
```

Add your credentials:
```env
DISCORD_TOKEN=your_discord_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

## GitHub Actions Setup

### 1. Add Repository Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:

| Secret Name | Value |
|------------|-------|
| `VPS_HOST` | `178.156.195.131` |
| `VPS_USER` | `root` |
| `VPS_PORT` | `22` |
| `VPS_SSH_KEY` | Your private SSH key (full content) |
| `DISCORD_TOKEN` | Your Discord bot token |
| `GEMINI_API_KEY` | Your Gemini API key |

### 2. Generate SSH Key (if needed)
```bash
# On your local machine
ssh-keygen -t rsa -b 4096 -f bananabot_deploy

# Copy public key to VPS
ssh-copy-id -i bananabot_deploy.pub root@178.156.195.131

# Copy private key content for GitHub secret
cat bananabot_deploy
```

## Managing the Bot on VPS

### Using Systemd (Recommended)

```bash
# Check status
sudo systemctl status bananabot

# View logs
sudo journalctl -u bananabot -f

# Restart bot
sudo systemctl restart bananabot

# Stop bot
sudo systemctl stop bananabot
```

## Automatic Deployment

Simply push to the `main` branch:
```bash
git add .
git commit -m "Update bot"
git push origin main
```

The GitHub Action will automatically deploy to your VPS!
