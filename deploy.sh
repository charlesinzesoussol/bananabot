#!/bin/bash

# BananaBot VPS Deployment Script
# Run this on your VPS at 178.156.195.131

set -e

echo "🍌 Starting BananaBot deployment..."

# Configuration
BOT_DIR="/opt/bananabot"
BOT_USER="bananabot"
REPO_URL="https://github.com/charlesinzesoussol/bananabot.git"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create bot user if it doesn't exist
if ! id "$BOT_USER" &>/dev/null; then
    echo "Creating bot user: $BOT_USER"
    useradd -r -m -s /bin/bash "$BOT_USER"
fi

# Create bot directory
if [ ! -d "$BOT_DIR" ]; then
    echo "Creating bot directory: $BOT_DIR"
    mkdir -p "$BOT_DIR"
    chown "$BOT_USER:$BOT_USER" "$BOT_DIR"
fi

# Switch to bot user and directory
cd "$BOT_DIR"

# Stop existing bot
echo "Stopping existing bot..."
pkill -f "python.*slash_bot.py" || true
pkill -f "python.*start.py" || true

# Clone or update repository
if [ ! -d ".git" ]; then
    echo "Cloning repository..."
    sudo -u "$BOT_USER" git clone "$REPO_URL" .
else
    echo "Updating repository..."
    sudo -u "$BOT_USER" git pull origin main
fi

# Setup Python virtual environment
if [ ! -d "venv_linux" ]; then
    echo "Creating virtual environment..."
    sudo -u "$BOT_USER" python3 -m venv venv_linux
fi

# Install dependencies
echo "Installing dependencies..."
sudo -u "$BOT_USER" bash -c "
    source venv_linux/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
"

# Check volume path
echo "Checking volume paths..."
sudo -u "$BOT_USER" python3 check_volume.py

# Create environment file (you need to fill this manually)
if [ ! -f ".env" ]; then
    echo "Creating .env template..."
    sudo -u "$BOT_USER" cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env file with your actual tokens!"
    echo "   nano $BOT_DIR/.env"
fi

# Create systemd service
cat > /etc/systemd/system/bananabot.service << EOF
[Unit]
Description=BananaBot Discord AI Image Generator
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
Environment=PATH=$BOT_DIR/venv_linux/bin
ExecStart=$BOT_DIR/venv_linux/bin/python $BOT_DIR/start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable bananabot
systemctl start bananabot

echo "✅ BananaBot deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file: nano $BOT_DIR/.env"
echo "2. Check status: systemctl status bananabot"
echo "3. View logs: journalctl -u bananabot -f"
echo "4. Restart bot: systemctl restart bananabot"