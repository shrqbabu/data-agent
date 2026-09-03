#!/bin/bash
set -e

echo "========================================="
echo "  Analytics Agent - VPS Setup Script"
echo "  (Optimized for 1GB RAM)"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- 1. System packages ---
echo -e "\n${YELLOW}[1/6] Installing system packages...${NC}"
sudo apt update -qq
sudo apt install -y -qq python3 python3-pip python3-venv git curl nginx certbot python3-certbot-nginx > /dev/null 2>&1
echo -e "${GREEN}Done${NC}"

# --- 2. Swap file (1GB RAM ke liye zaroori) ---
echo -e "\n${YELLOW}[2/6] Setting up 1GB swap...${NC}"
if [ ! -f /swapfile ]; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    echo -e "${GREEN}Swap created${NC}"
else
    echo -e "${GREEN}Swap already exists${NC}"
fi

# --- 3. Clone repo ---
echo -e "\n${YELLOW}[3/6] Cloning repository...${NC}"
REPO_DIR="/opt/analytics-agent"
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    git pull origin main
else
    sudo git clone https://github.com/shrqbabu/data-agent.git "$REPO_DIR"
    sudo chown -R $USER:$USER "$REPO_DIR"
fi
echo -e "${GREEN}Done${NC}"

# --- 4. Python venv + dependencies ---
echo -e "\n${YELLOW}[4/6] Setting up Python environment...${NC}"
cd "$REPO_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet -r requirements.txt
echo -e "${GREEN}Done${NC}"

# --- 5. .env file ---
echo -e "\n${YELLOW}[5/6] Checking .env file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Edit /opt/analytics-agent/backend/.env with your keys!${NC}"
    echo -e "${YELLOW}Run: nano /opt/analytics-agent/backend/.env${NC}"
else
    echo -e "${GREEN}.env already exists${NC}"
fi

# --- 6. Systemd service ---
echo -e "\n${YELLOW}[6/6] Creating systemd service...${NC}"
sudo tee /etc/systemd/system/analytics-backend.service > /dev/null <<EOF
[Unit]
Description=Analytics Agent Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$REPO_DIR/backend
ExecStart=$REPO_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
EnvironmentFile=$REPO_DIR/backend/.env
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable analytics-backend
echo -e "${GREEN}Service created${NC}"

# --- 7. Nginx reverse proxy ---
echo -e "\n${YELLOW}Configuring Nginx...${NC}"
sudo tee /etc/nginx/sites-available/analytics-backend > /dev/null <<'NGINX'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 15s;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/analytics-backend /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx
echo -e "${GREEN}Nginx configured${NC}"

# --- Firewall ---
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file:"
echo "   nano /opt/analytics-agent/backend/.env"
echo ""
echo "2. Start the backend:"
echo "   sudo systemctl start analytics-backend"
echo ""
echo "3. Check status:"
echo "   sudo systemctl status analytics-backend"
echo ""
echo "4. Test:"
echo "   curl http://localhost/health"
echo ""
echo "5. Your API_URL for GitHub Secrets:"
echo "   http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_VPS_IP')"
echo ""
echo "6. (Optional) Add SSL with domain:"
echo "   sudo certbot --nginx -d yourdomain.com"
echo ""
