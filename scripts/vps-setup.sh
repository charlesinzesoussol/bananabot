#!/bin/bash

# VPS Setup Script for BananaBot
# Run this once on your VPS to set up the environment

echo "🍌 BananaBot VPS Setup Script"
echo "=============================="

# Update system
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Create bot directory
echo "Creating bot directory..."
mkdir -p ~/bananabot
cd ~/bananabot

# Clone repository
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    git clone https://github.com/charlesinzesoussol/bananabot.git .
else
    echo "Repository already exists, pulling latest..."
    git pull origin main
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  IMPORTANT: Create .env file with your credentials:"
    echo "nano .env"
    echo ""
    echo "Add these lines:"
    echo "DISCORD_TOKEN=your_discord_bot_token"
    echo "GEMINI_API_KEY=your_gemini_api_key"
    echo ""
    read -p "Press enter when you've created the .env file..."
fi

# Set up systemd service
echo "Setting up systemd service..."
sudo cp bananabot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bananabot
sudo systemctl start bananabot

# Check status
echo ""
echo "Checking service status..."
sleep 3
if sudo systemctl is-active --quiet bananabot; then
    echo "✅ BananaBot is running!"
    sudo systemctl status bananabot --no-pager
    echo ""
    echo "Useful commands:"
    echo "  View logs:        sudo journalctl -u bananabot -f"
    echo "  Restart bot:      sudo systemctl restart bananabot"
    echo "  Stop bot:         sudo systemctl stop bananabot"
    echo "  Start bot:        sudo systemctl start bananabot"
    echo "  Check status:     sudo systemctl status bananabot"
else
    echo "❌ BananaBot failed to start. Check logs:"
    sudo journalctl -u bananabot -n 50 --no-pager
fi

echo ""
echo "🍌 Setup complete!"