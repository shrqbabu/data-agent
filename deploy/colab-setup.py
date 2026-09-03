# Analytics Agent — Google Colab Setup
# Copy this into a Colab notebook cell-by-cell

# ============================================================
# CELL 1: Install dependencies
# ============================================================
!pip install -q uvicorn pyngrok

# ============================================================
# CELL 2: Clone repo
# ============================================================
!git clone https://github.com/shrqbabu/data-agent.git /content/data-agent
%cd /content/data-agent/backend
!pip install -q -r requirements.txt

# ============================================================
# CELL 3: Configure — FILL YOUR KEYS HERE
# ============================================================
import os

os.environ["SUPABASE_URL"]              = "https://TUMHARA_PROJECT.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "TUMHARA_SERVICE_ROLE_KEY"
os.environ["SUPABASE_PUBLISHABLE_KEY"]  = "TUMHARA_ANON_KEY"
os.environ["SUPABASE_JWT_SECRET"]       = "TUMHARA_JWT_SECRET"
os.environ["LLM_ENABLED"]               = "false"
os.environ["MAX_UPLOAD_MB"]             = "100"
os.environ["JOB_CONCURRENCY"]           = "1"
os.environ["APP_ENV"]                   = "production"
os.environ["CORS_ORIGINS"]              = "*"

print("✅ Config set")

# ============================================================
# CELL 4: Start backend with ngrok tunnel
# ============================================================
from pyngrok import ngrok
import subprocess, threading, time

# Kill any existing tunnels
ngrok.kill()

# Start uvicorn in background
def run_server():
    subprocess.run([
        "uvicorn", "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--workers", "1"
    ])

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

# Wait for server to start
time.sleep(5)

# Create ngrok tunnel
public_url = ngrok.connect(8000, bind_tls=True).public_url
print(f"\n{'='*50}")
print(f"🚀 Backend is LIVE at:")
print(f"   {public_url}")
print(f"{'='*50}")
print(f"\n📋 GitHub Secret mein API_URL yeh daalo:")
print(f"   {public_url}")
print(f"\n📱 Android app mein bhi yeh URL use hoga")
print(f"{'='*50}")

# ============================================================
# CELL 5: Test health endpoint
# ============================================================
import requests
resp = requests.get(f"{public_url}/health")
print(f"Health check: {resp.status_code} — {resp.text}")

# ============================================================
# CELL 6: Keep alive (run this cell to prevent Colab timeout)
# ============================================================
# Colab auto-disconnects after idle. Yeh cell mat stop karo.
import time
while True:
    time.sleep(60)
    print("⏳ Backend running...", end="\r")
