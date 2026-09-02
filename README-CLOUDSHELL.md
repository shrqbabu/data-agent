# Google Cloud Shell Build Guide

## Quick Start in Cloud Shell

Google Cloud Shell mein build karne ke liye yeh simple steps follow karo:

### 1. Open Google Cloud Shell

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the **Cloud Shell** icon in top-right corner (">_")
3. Wait for shell to activate

### 2. Clone Your Repository

```bash
# If repo is on GitHub
git clone https://github.com/your-username/analytics-agent.git
cd analytics-agent

# Or upload files manually
# Click the three dots menu → Upload → Select files/folder
```

### 3. Build Everything

```bash
# Make script executable
chmod +x build-cloudshell.sh

# Run build
./build-cloudshell.sh
```

Yeh script automatically:
- ✅ Android APK build karega (Docker se)
- ✅ Backend Docker image banega
- ✅ Sab kuch ready ho jayega

### 4. Download APK

Build complete hone ke baad:

```bash
# Cloud Shell se APK download karo
cloudshell download android/app/build/outputs/apk/debug/app-debug.apk
```

Ya manually:
1. Cloud Shell menu → **Download file**
2. Path enter karo: `android/app/build/outputs/apk/debug/app-debug.apk`

### 5. Deploy Backend (Optional)

Agar backend bhi deploy karna hai Cloud Run pe:

```bash
# Docker image push karo Google Container Registry mein
docker push gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest

# Deploy to Cloud Run
gcloud run deploy analytics-agent-backend \
  --image gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SUPABASE_URL=https://your-project.supabase.co,SUPABASE_SERVICE_KEY=your-service-key,JWT_SECRET=your-secret,ANTHROPIC_API_KEY=your-api-key
```

## Environment Variables Setup

Agar APK mein Supabase credentials inject karne hain:

```bash
# Set environment variables
export ANALYTICS_AGENT_SUPABASE_URL="https://your-project.supabase.co"
export ANALYTICS_AGENT_SUPABASE_KEY="your-anon-key"
export ANALYTICS_AGENT_API_URL="https://your-backend-url.run.app"

# Build with credentials
cd android
./gradlew :app:assembleDebug \
  -PANALYTICS_AGENT_SUPABASE_URL="$ANALYTICS_AGENT_SUPABASE_URL" \
  -PANALYTICS_AGENT_SUPABASE_KEY="$ANALYTICS_AGENT_SUPABASE_KEY" \
  -PANALYTICS_AGENT_API_URL="$ANALYTICS_AGENT_API_URL"
cd ..
```

## Cloud Shell Tips

### Free Tier Limits
- **Session**: 5 hours of inactivity = automatic shutdown
- **Storage**: 5GB home directory (persists across sessions)
- **Machine**: 2GB RAM (boost available on request)

### Save Build Artifacts

```bash
# Create persistent directory
mkdir -p ~/builds
cp android/app/build/outputs/apk/debug/app-debug.apk ~/builds/app-$(date +%Y%m%d).apk

# List saved builds
ls -lh ~/builds/
```

### Speed Up Builds

```bash
# Use Gradle daemon (faster subsequent builds)
cd android
./gradlew :app:assembleDebug --daemon

# Or disable daemon to save memory
./gradlew :app:assembleDebug --no-daemon
```

### Check Docker

```bash
# Verify Docker is working
docker --version
docker ps

# Pull Android SDK image beforehand (optional, faster build)
docker pull ghcr.io/cirruslabs/android-sdk:35
```

## Troubleshooting

### "Docker not available"

Cloud Shell should have Docker pre-installed. If not:

```bash
# Check Docker status
sudo systemctl status docker

# Start Docker
sudo systemctl start docker
```

### Out of Memory

```bash
# Use Gradle with less memory
cd android
./gradlew :app:assembleDebug -Dorg.gradle.jvmargs=-Xmx1024m --no-daemon
```

### Build Too Slow

Cloud Shell has limited resources. For faster builds:
1. Use Cloud Build instead (see [README-DEPLOYMENT.md](README-DEPLOYMENT.md))
2. Request boost mode: Click "⋮" → "Boost Cloud Shell"

### Session Timeout

Cloud Shell disconnects after 20 minutes of inactivity. To keep alive:

```bash
# Run in tmux (survives disconnects)
tmux new -s build
./build-cloudshell.sh

# Detach: Ctrl+B then D
# Reattach after reconnecting: tmux attach -t build
```

### Gradle Errors

```bash
# Clean build
cd android
./gradlew clean
./gradlew :app:assembleDebug --refresh-dependencies

# Check Java version (should be 17)
java -version
```

## Build Time Estimates

- **First Build**: ~8-12 minutes
  - Docker image pull: ~2-3 min
  - Gradle dependencies: ~3-5 min
  - APK compilation: ~3-4 min

- **Subsequent Builds**: ~3-5 minutes
  - Docker cache: instant
  - Gradle cache: ~1-2 min
  - APK compilation: ~2-3 min

## Alternative: Manual Build (No Docker)

Agar Docker issues hain:

```bash
# Install Android SDK manually (not recommended, slow)
cd android

# Use existing Gradle wrapper
chmod +x gradlew
./gradlew :app:assembleDebug --stacktrace

# APK location same hai
ls -lh app/build/outputs/apk/debug/app-debug.apk
```

## Deploy Backend Options

### Option 1: Cloud Run (Recommended)

```bash
docker push gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest

gcloud run deploy analytics-agent-backend \
  --image gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest \
  --platform managed \
  --region us-central1
```

### Option 2: Compute Engine

```bash
# Create VM
gcloud compute instances create analytics-backend \
  --machine-type=e2-medium \
  --image-family=cos-stable \
  --image-project=cos-cloud

# Deploy container
gcloud compute ssh analytics-backend -- \
  docker run -d -p 8000:8000 \
  gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest
```

### Option 3: GKE (For Production)

```bash
# Create cluster
gcloud container clusters create analytics-cluster --num-nodes=3

# Deploy
kubectl create deployment analytics-backend \
  --image=gcr.io/$(gcloud config get-value project)/analytics-agent-backend:latest
```

## Cost

**Cloud Shell**: FREE
- Unlimited build time
- 5GB persistent storage
- Pre-installed tools

**Storage** (if you push to GCR):
- Container Registry: ~$0.026/GB/month
- Backend image size: ~500MB = $0.013/month

**Deployment** (if you use Cloud Run):
- Free tier: 2M requests/month
- Beyond: ~$0.00002400/request

## Next Steps

1. ✅ Build APK in Cloud Shell: `./build-cloudshell.sh`
2. ✅ Download APK: `cloudshell download android/app/build/outputs/apk/debug/app-debug.apk`
3. ✅ Install on Android device and test
4. ✅ (Optional) Deploy backend to Cloud Run

Complete Cloud Build docs: [README-DEPLOYMENT.md](README-DEPLOYMENT.md)
