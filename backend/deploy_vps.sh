#!/usr/bin/env bash
# ==============================================================================
# Analytics Agent Backend - 1-Click VPS Deployer
# ==============================================================================
set -e

echo "🚀 Deploying Analytics Agent Backend on VPS..."

# 1. Update system packages
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y curl wget git

# 2. Install Docker & Compose if missing
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# 3. Build & launch container
echo "🏗️ Building and starting Docker container..."
docker compose down || true
docker compose up -d --build

IP=$(curl -s ifconfig.me || echo "YOUR_VPS_IP")
echo "✅ Analytics Agent API is live at http://$IP:8000"
echo "🔍 Health check: http://$IP:8000/health"
echo "📖 Swagger Docs: http://$IP:8000/docs"
