#!/usr/bin/env bash
set -e

echo "=========================================="
echo "🚀 Building Analytics Agent in Google Cloud Shell"
echo "=========================================="

# Check if running in Cloud Shell
if [ -n "$CLOUD_SHELL" ]; then
    echo "✅ Running in Google Cloud Shell"
else
    echo "⚠️  Not detected as Cloud Shell, but continuing anyway..."
fi

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
echo "📋 Project ID: $PROJECT_ID"

# Build Android APK using Docker
echo ""
echo "=========================================="
echo "📦 Building Android APK..."
echo "=========================================="

if command -v docker &> /dev/null; then
    echo "Using Docker with Android SDK 35..."
    docker run --rm \
      -v "$(pwd)/android":/workspace \
      -w /workspace \
      ghcr.io/cirruslabs/android-sdk:35 \
      bash -c "
        set -e
        echo '➜ Setting up Gradle wrapper...'
        gradle wrapper --gradle-version 8.11.1 || true
        chmod +x ./gradlew

        echo '➜ Building APK...'
        ./gradlew :app:assembleDebug --stacktrace --no-daemon
      "
else
    echo "❌ Docker not available. Please enable Docker in Cloud Shell."
    exit 1
fi

# Build Backend Docker Image
echo ""
echo "=========================================="
echo "🐳 Building Backend Docker Image..."
echo "=========================================="

cd backend
docker build -t gcr.io/${PROJECT_ID}/analytics-agent-backend:latest .
cd ..

echo ""
echo "=========================================="
echo "✅ Build Complete!"
echo "=========================================="
echo ""
echo "📱 Android APK: android/app/build/outputs/apk/debug/app-debug.apk"
echo "🐳 Docker Image: gcr.io/${PROJECT_ID}/analytics-agent-backend:latest"
echo ""
echo "Next Steps:"
echo ""
echo "1. Download APK:"
echo "   cloudshell download android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "2. Push Docker image to GCR:"
echo "   docker push gcr.io/${PROJECT_ID}/analytics-agent-backend:latest"
echo ""
echo "3. Deploy to Cloud Run:"
echo "   gcloud run deploy analytics-agent-backend \\"
echo "     --image gcr.io/${PROJECT_ID}/analytics-agent-backend:latest \\"
echo "     --platform managed \\"
echo "     --region us-central1 \\"
echo "     --allow-unauthenticated \\"
echo "     --set-env-vars SUPABASE_URL=...,SUPABASE_SERVICE_KEY=...,JWT_SECRET=...,ANTHROPIC_API_KEY=..."
echo "=========================================="
