#!/bin/bash
set -e

TOKEN="${1:-}"
if [ -z "$TOKEN" ]; then
    echo "Error: Discord token required"
    echo "Usage: bash deploy-oracle.sh YOUR_DISCORD_TOKEN"
    exit 1
fi

echo "=========================================="
echo "ALEA Bot Oracle Deployment"
echo "=========================================="

echo "[1/7] Updating system..."
sudo apt update -qq 2>/dev/null
sudo apt install -y python3 python3-pip git 2>/dev/null

echo "[2/7] Creating deploy user..."
sudo useradd -m -s /bin/bash deploy 2>/dev/null || echo "Deploy user already exists"

echo "[3/7] Cloning repository..."
if [ ! -d "/home/deploy/alea-dice-bot" ]; then
  sudo -u deploy git clone https://github.com/ThatFabio/alea-dice-bot.git /home/deploy/alea-dice-bot 2>/dev/null
else
  cd /home/deploy/alea-dice-bot && sudo -u deploy git pull 2>/dev/null && cd -
fi

echo "[4/7] Installing Python dependencies..."
cd /home/deploy/alea-dice-bot
sudo -u deploy pip install -r requirements.txt -q 2>/dev/null

echo "[5/7] Creating systemd service..."
sudo tee /etc/systemd/system/alea-bot.service > /dev/null << SERVICEEOF
[Unit]
Description=ALEA Discord Bot
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/home/deploy/alea-dice-bot
ExecStart=/usr/bin/python3 /home/deploy/alea-dice-bot/main.py
Restart=always
RestartSec=10
Environment="DISCORD_BOT_TOKEN=$TOKEN"

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo "[6/7] Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable alea-bot.service 2>/dev/null

echo "[7/7] Starting bot..."
sudo systemctl start alea-bot.service

sleep 2
echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
sudo systemctl status alea-bot.service --no-pager
echo ""
echo "Bot is now running 24/7 on Oracle!"
echo "Check logs: sudo journalctl -u alea-bot.service -f"
