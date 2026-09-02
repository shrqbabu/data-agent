# Google Cloud Build Deployment Guide

## Prerequisites

1. **Google Cloud Project**
   - Create a project at [console.cloud.google.com](https://console.cloud.google.com)
   - Note your Project ID

2. **Install gcloud CLI**
   ```bash
   # Download from: https://cloud.google.com/sdk/docs/install
   # After installation, authenticate:
   gcloud auth login
   gcloud auth application-default login
   ```

3. **Environment Variables**
   Set these before deploying:
   ```bash
   export GCLOUD_PROJECT_ID="your-project-id"
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_KEY="your-anon-key"
   export API_URL="https://your-backend-url"
   export GCS_BUCKET="analytics-agent-artifacts"  # Optional, default provided
   ```

## Quick Deployment

### Option 1: Using the Automated Script

```bash
# Set environment variables first
export GCLOUD_PROJECT_ID="your-project-id"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export API_URL="https://your-backend-url"

# Run deployment script
./deploy-gcloud.sh
```

### Option 2: Manual Cloud Build

```bash
# Enable required APIs
gcloud services enable cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    run.googleapis.com

# Create GCS bucket for APK storage
gsutil mb -p your-project-id -l us-central1 gs://analytics-agent-artifacts

# Submit build
gcloud builds submit . \
    --config=cloudbuild.yaml \
    --substitutions=_GCS_BUCKET="analytics-agent-artifacts",_SUPABASE_URL="https://your-project.supabase.co",_SUPABASE_KEY="your-anon-key",_API_URL="https://your-backend-url"
```

## What Gets Built

The Cloud Build process creates:

1. **Android APK** (Debug)
   - Built using Android SDK 35 + Gradle 8.11.1
   - Stored in: `gs://analytics-agent-artifacts/apk-builds/BUILD_ID/app-debug.apk`

2. **Backend Docker Image**
   - Image: `gcr.io/PROJECT_ID/analytics-agent-backend:latest`
   - Tagged with commit SHA: `gcr.io/PROJECT_ID/analytics-agent-backend:SHORT_SHA`

## Deploying Backend to Cloud Run

After the build completes, deploy the backend:

```bash
gcloud run deploy analytics-agent-backend \
    --image gcr.io/PROJECT_ID/analytics-agent-backend:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "SUPABASE_URL=https://your-project.supabase.co,SUPABASE_SERVICE_KEY=your-service-key,JWT_SECRET=your-jwt-secret,ANTHROPIC_API_KEY=your-api-key"
```

### Backend Environment Variables

Required environment variables for Cloud Run:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Supabase service role key (NOT anon key)
- `JWT_SECRET`: Secret for JWT token signing
- `ANTHROPIC_API_KEY`: Anthropic API key for AI features
- `CORS_ORIGINS`: Comma-separated allowed origins

Optional:
- `APP_ENV`: Set to `production`
- `LOG_LEVEL`: Set to `INFO` or `DEBUG`

## Viewing Build Status

```bash
# List recent builds
gcloud builds list --limit=5

# View specific build log
gcloud builds log BUILD_ID

# View latest build log
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)')
```

## Downloading APK

```bash
# List all builds
gsutil ls gs://analytics-agent-artifacts/apk-builds/

# Download specific APK
gsutil cp gs://analytics-agent-artifacts/apk-builds/BUILD_ID/app-debug.apk ./app-debug.apk
```

## Build Configuration

Edit [cloudbuild.yaml](cloudbuild.yaml) to customize:

- **Machine Type**: Currently `E2_HIGHCPU_8` (8 vCPU)
  - Options: `E2_HIGHCPU_8`, `E2_HIGHCPU_32`, `N1_HIGHCPU_8`, etc.
  
- **Timeout**: Currently 30 minutes (1800s)
  - Adjust if builds take longer

- **Build Steps**: 4 steps
  1. Build Android APK
  2. Build Backend Docker image
  3. Push Docker image to GCR
  4. Upload APK to Cloud Storage

## Substitution Variables

Default values in `cloudbuild.yaml`:
```yaml
substitutions:
  _GCS_BUCKET: 'analytics-agent-artifacts'
  _SUPABASE_URL: ''
  _SUPABASE_KEY: ''
  _API_URL: ''
```

Override during build:
```bash
gcloud builds submit . \
    --config=cloudbuild.yaml \
    --substitutions=_GCS_BUCKET="my-bucket",_SUPABASE_URL="...",_SUPABASE_KEY="...",_API_URL="..."
```

## Cost Estimation

- **Cloud Build**: ~$0.003/build-minute on `E2_HIGHCPU_8`
  - Typical build: 5-10 minutes = $0.015-$0.030 per build
  
- **Cloud Storage**: $0.020/GB/month
  - APK size: ~50MB = $0.001/month per APK
  
- **Container Registry**: $0.026/GB/month
  - Docker image: ~500MB = $0.013/month

- **Cloud Run** (if deployed):
  - Free tier: 2M requests/month, 360,000 GB-seconds/month
  - Beyond free tier: $0.00002400/request + $0.00001800/GB-second

## Troubleshooting

### Build Fails at Android Step

```bash
# Check Gradle version compatibility
# Edit cloudbuild.yaml and adjust Gradle version if needed
gradle wrapper --gradle-version 8.11.1
```

### Docker Build Fails

```bash
# Test locally first
cd backend
docker build -t analytics-agent-backend:test .
docker run -p 8000:8000 analytics-agent-backend:test
```

### Permission Denied

```bash
# Grant Cloud Build service account required permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member=serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
    --role=roles/storage.admin
```

### GCS Bucket Access Denied

```bash
# Make bucket accessible to Cloud Build
gsutil iam ch serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com:objectCreator \
    gs://analytics-agent-artifacts
```

## CI/CD Integration

To trigger builds automatically on git push, connect to Cloud Build:

```bash
# Connect repository
gcloud builds triggers create github \
    --repo-name=analytics-agent \
    --repo-owner=YOUR_GITHUB_USERNAME \
    --branch-pattern="^main$" \
    --build-config=cloudbuild.yaml
```

## Local Testing with Cloud Shell

Use the existing [build-cloudshell.sh](build-cloudshell.sh) script for testing in Google Cloud Shell:

```bash
./build-cloudshell.sh
```

This builds the Android APK using Docker in Cloud Shell environment.

## Support

For issues:
1. Check [cloudbuild.yaml](cloudbuild.yaml) configuration
2. Review build logs: `gcloud builds log BUILD_ID`
3. Verify environment variables are set correctly
4. Check [Google Cloud Build Documentation](https://cloud.google.com/build/docs)
