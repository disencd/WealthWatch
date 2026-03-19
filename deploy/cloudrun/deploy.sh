#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# WealthWatch — Build & deploy API to Cloud Run
# Uses SQLite with GCS FUSE volume mount (no external database)
#
# Usage:
#   export GCP_PROJECT=my-project-id
#   bash deploy/cloudrun/deploy.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="wealthwatch-api"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/wealthwatch/${SERVICE}"
TAG="${IMAGE}:$(git rev-parse --short HEAD 2>/dev/null || echo latest)"
BUCKET="${GCP_PROJECT}-wealthwatch-data"

echo "══════════════════════════════════════════════════"
echo "  Deploying WealthWatch API to Cloud Run"
echo "  Image   : $TAG"
echo "  Service : $SERVICE"
echo "  Region  : $REGION"
echo "  DB      : SQLite on GCS (gs://$BUCKET)"
echo "══════════════════════════════════════════════════"

# ── Build & push ─────────────────────────────────────────────────────
echo "→ Building container image..."
docker build -f Dockerfile.cloudrun -t "$TAG" .
docker push "$TAG"

# ── Deploy to Cloud Run ──────────────────────────────────────────────
echo "→ Deploying to Cloud Run..."
gcloud run deploy "$SERVICE" \
  --image="$TAG" \
  --region="$REGION" \
  --project="$PROJECT" \
  --platform=managed \
  --execution-environment=gen2 \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=1 \
  --concurrency=80 \
  --timeout=60 \
  --cpu-boost \
  --set-env-vars="\
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-},\
SQLITE_DB_PATH=/data/wealthwatch.db" \
  --set-secrets="\
JWT_SECRET=wealthwatch-jwt-secret:latest" \
  --add-volume=name=sqlite-data,type=cloud-storage,bucket="$BUCKET" \
  --add-volume-mount=volume=sqlite-data,mount-path=/data

# ── Print URL ────────────────────────────────────────────────────────
URL=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" --project="$PROJECT" \
  --format='value(status.url)')

echo ""
echo "══════════════════════════════════════════════════"
echo "  Deployed successfully!"
echo ""
echo "  API URL  : $URL"
echo "  Health   : $URL/health"
echo "  Swagger  : $URL/docs"
echo "  Database : SQLite on GCS (gs://$BUCKET)"
echo ""
echo "  Update ALLOWED_ORIGINS with your Firebase Hosting URL:"
echo "    gcloud run services update $SERVICE \\"
echo "      --update-env-vars ALLOWED_ORIGINS=https://your-app.web.app \\"
echo "      --region $REGION --project $PROJECT"
echo "══════════════════════════════════════════════════"
