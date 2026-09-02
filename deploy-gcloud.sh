#!/usr/bin/env bash
set -e

echo "=========================================="
echo "🚀 Deploying Analytics Agent to Google Cloud"
echo "=========================================="

# Configuration
PROJECT_ID="${GCLOUD_PROJECT_ID:-your-project-id}"
REGION="${GCLOUD_REGION:-us-central1}"
GCS_BUCKET="${GCS_BUCKET:-analytics-agent-artifacts}"
SUPABASE_URL="${SUPABASE_URL:-}"
SUPABASE_KEY="${SUPABASE_KEY:-}"
API_URL="${API_URL:-}"

echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "GCS Bucket: $GCS_BUCKET"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "Setting project..."
gcloud config set project "$PROJECT_ID"

# Create GCS bucket if it doesn't exist
echo "Checking GCS bucket..."
if ! gsutil ls -b "gs://${GCS_BUCKET}" &> /dev/null; then
    echo "Creating GCS bucket: gs://${GCS_BUCKET}"
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${GCS_BUCKET}"
else
    echo "GCS bucket already exists: gs://${GCS_BUCKET}"
fi

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    run.googleapis.com \
    storage-api.googleapis.com

# Submit build to Cloud Build
echo ""
echo "=========================================="
echo "📦 Submitting build to Cloud Build..."
echo "=========================================="

gcloud builds submit . \
    --config=cloudbuild.yaml \
    --substitutions=_GCS_BUCKET="$GCS_BUCKET",_SUPABASE_URL="$SUPABASE_URL",_SUPABASE_KEY="$SUPABASE_KEY",_API_URL="$API_URL"

echo ""
echo "=========================================="
echo "✅ Build submitted successfully!"
echo ""
echo "To view build status:"
echo "  gcloud builds list --limit=5"
echo ""
echo "To view build logs:"
echo "  gcloud builds log \$(gcloud builds list --limit=1 --format='value(id)')"
echo ""
echo "To list generated APKs:"
echo "  gsutil ls gs://${GCS_BUCKET}/apk-builds/"
echo ""
echo "To deploy backend to Cloud Run:"
echo "  gcloud run deploy analytics-agent-backend \\"
echo "    --image gcr.io/${PROJECT_ID}/analytics-agent-backend:latest \\"
echo "    --platform managed \\"
echo "    --region ${REGION} \\"
echo "    --allow-unauthenticated"
echo "=========================================="
