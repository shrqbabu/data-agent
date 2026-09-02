#!/usr/bin/env bash
set -e

echo "=========================================="
echo "🚀 Building Analytics Agent in Google Cloud Shell"
echo "=========================================="

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo 'analytics-agent')}"
echo "📋 Project ID: $PROJECT_ID"

# Step 1: Build Android APK
echo ""
echo "=========================================="
echo "📦 Step 1: Building Android APK..."
echo "=========================================="

# Clean up stale locks and previous build folders on host
echo "➜ Cleaning previous locks..."
rm -rf android/.gradle android/app/build

if command -v docker &> /dev/null; then
    echo "Using Docker container: ghcr.io/cirruslabs/android-sdk:35"
    docker run --rm \
      -v "$(pwd)/android":/workspace \
      -w /workspace \
      ghcr.io/cirruslabs/android-sdk:35 \
      bash -c '
        set -e
        export GRADLE_USER_HOME=/tmp/.gradle
        rm -rf /workspace/.gradle /workspace/app/build

        echo "➜ Installing Gradle 8.11.1..."
        if ! command -v gradle &> /dev/null; then
            mkdir -p /opt/gradle
            curl -sSL https://services.gradle.org/distributions/gradle-8.11.1-bin.zip -o /tmp/gradle.zip
            unzip -q -o /tmp/gradle.zip -d /opt/gradle
            rm -f /tmp/gradle.zip
            export PATH=/opt/gradle/gradle-8.11.1/bin:$PATH
        fi

        echo "➜ Compiling Android APK (:app:assembleDebug)..."
        gradle :app:assembleDebug --stacktrace --no-daemon
      '
else
    echo "❌ Docker not available."
    exit 1
fi

# Step 2: Build Backend Docker Image
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
    echo "📥 Run this command to download APK:"
    echo "   cloudshell download $APK_PATH"
fi
echo "=========================================="
