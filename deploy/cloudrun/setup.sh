#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# WealthWatch — One-time GCP project setup for Cloud Run deployment
# Uses SQLite + GCS FUSE volume mount (no external database = $0/month)
#
# Usage:
#   export GCP_PROJECT=my-project-id
#   bash deploy/cloudrun/setup.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="wealthwatch-api"
BUCKET="${GCP_PROJECT}-wealthwatch-data"

echo "══════════════════════════════════════════════════"
echo "  WealthWatch — GCP Setup (SQLite + GCS)"
echo "  Project : $PROJECT"
echo "  Region  : $REGION"
echo "  Bucket  : $BUCKET"
echo "══════════════════════════════════════════════════"

# ── Enable APIs ──────────────────────────────────────────────────────
echo "→ Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  --project="$PROJECT"

# ── Artifact Registry ────────────────────────────────────────────────
echo "→ Creating Artifact Registry repo..."
gcloud artifacts repositories describe wealthwatch \
  --location="$REGION" --project="$PROJECT" 2>/dev/null || \
gcloud artifacts repositories create wealthwatch \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT" \
  --description="WealthWatch container images"

# ── GCS Bucket for SQLite data ───────────────────────────────────────
echo "→ Creating GCS bucket for SQLite data..."
gcloud storage buckets describe "gs://$BUCKET" 2>/dev/null || \
gcloud storage buckets create "gs://$BUCKET" \
  --location="$REGION" \
  --project="$PROJECT" \
  --uniform-bucket-level-access

# ── Store JWT secret in Secret Manager ───────────────────────────────
echo "→ Storing JWT secret in Secret Manager..."
JWT_SECRET=$(openssl rand -base64 32)

_upsert_secret() {
  local name="$1"
  echo -n "$2" | gcloud secrets create "$name" \
    --data-file=- --project="$PROJECT" 2>/dev/null || \
  echo -n "$2" | gcloud secrets versions add "$name" \
    --data-file=- --project="$PROJECT"
}

_upsert_secret "wealthwatch-jwt-secret" "$JWT_SECRET"

# ── Grant Cloud Run service account access ───────────────────────────
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "→ Granting IAM roles to $SA..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor" --quiet

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role="roles/storage.objectAdmin" --quiet

echo ""
echo "══════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  AR repo  : ${REGION}-docker.pkg.dev/${PROJECT}/wealthwatch"
echo "  Bucket   : gs://$BUCKET"
echo "  Database : SQLite (stored in GCS bucket)"
echo ""
echo "  Next: run  deploy/cloudrun/deploy.sh"
echo "══════════════════════════════════════════════════"
