#!/usr/bin/env bash
set -e

echo "=========================================="
echo "🚀 Building Analytics Agent in Google Cloud Shell"
echo "=========================================="

# Check if running in Cloud Shell
if [ -n "$CLOUD_SHELL" ]; then
    echo "✅ Running in Google Cloud Shell"
else
    echo "ℹ️  Environment: Standard Linux / Cloud Shell"
fi

# Project ID setup
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo 'analytics-agent')}"
echo "📋 Project ID: $PROJECT_ID"

# Build Android APK using Docker with Android SDK 35
echo ""
echo "=========================================="
echo "📦 Step 1: Building Android APK..."
echo "=========================================="

if command -v docker &> /dev/null; then
    echo "Using Docker container: ghcr.io/cirruslabs/android-sdk:35"
    docker run --rm \
      -v "$(pwd)/android":/workspace \
      -w /workspace \
      ghcr.io/cirruslabs/android-sdk:35 \
      bash -c '
        set -e
        echo "➜ Installing Gradle 8.11.1 inside build container..."
        if ! command -v gradle &> /dev/null; then
            mkdir -p /opt/gradle
            curl -sSL https://services.gradle.org/distributions/gradle-8.11.1-bin.zip -o /tmp/gradle.zip
            unzip -q -o /tmp/gradle.zip -d /opt/gradle
            rm -f /tmp/gradle.zip
            export PATH=/opt/gradle/gradle-8.11.1/bin:$PATH
        fi

        echo "➜ Generating official Gradle wrapper..."
        gradle wrapper --gradle-version 8.11.1 --distribution-type bin || true
        chmod +x ./gradlew || true

        echo "➜ Compiling Android APK (:app:assembleDebug)..."
        gradle :app:assembleDebug --stacktrace --no-daemon
      '
else
    echo "❌ Docker not available in this environment."
    exit 1
fi

# Build Backend Docker Image
echo ""
echo "=========================================="
echo "🐳 Step 2: Building Backend Docker Image..."
echo "=========================================="

cd backend
docker build -t "gcr.io/${PROJECT_ID}/analytics-agent-backend:latest" .
cd ..

echo ""
echo "=========================================="
echo "🎉 Build Complete!"
echo "=========================================="
APK_PATH="android/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK_PATH" ]; then
    echo "📱 Android APK generated at:"
    echo "   $APK_PATH"
    echo ""
    echo "📥 To download in Cloud Shell, run:"
    echo "   cloudshell download $APK_PATH"
else
    echo "⚠️ APK path check: android/app/build/outputs/apk/debug/"
fi
echo ""
echo "🐳 Backend Docker Image:"
echo "   gcr.io/${PROJECT_ID}/analytics-agent-backend:latest"
echo "=========================================="
