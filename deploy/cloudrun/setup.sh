#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# WealthWatch — One-time GCP project setup for Cloud Run deployment
# Uses Neon/Supabase free-tier PostgreSQL (no Cloud SQL = $0/month)
#
# Usage:
#   export GCP_PROJECT=my-project-id
#   export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require"
#   bash deploy/cloudrun/setup.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
PROJECT="${GCP_PROJECT:?Set GCP_PROJECT}"
REGION="${GCP_REGION:-us-central1}"
SERVICE="wealthwatch-api"
DATABASE_URL="${DATABASE_URL:?Set DATABASE_URL (Neon or Supabase connection string)}"

echo "══════════════════════════════════════════════════"
echo "  WealthWatch — GCP Setup (Neon/Supabase DB)"
echo "  Project : $PROJECT"
echo "  Region  : $REGION"
echo "  DB      : external (Neon/Supabase)"
echo "══════════════════════════════════════════════════"

# ── Enable APIs ──────────────────────────────────────────────────────
echo "→ Enabling GCP APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
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

# ── Store secrets in Secret Manager ──────────────────────────────────
echo "→ Storing secrets in Secret Manager..."
JWT_SECRET=$(openssl rand -base64 32)

_upsert_secret() {
  local name="$1"
  echo -n "$2" | gcloud secrets create "$name" \
    --data-file=- --project="$PROJECT" 2>/dev/null || \
  echo -n "$2" | gcloud secrets versions add "$name" \
    --data-file=- --project="$PROJECT"
}

_upsert_secret "wealthwatch-database-url" "$DATABASE_URL"
_upsert_secret "wealthwatch-jwt-secret"   "$JWT_SECRET"

# ── Grant Cloud Run service account access ───────────────────────────
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "→ Granting IAM roles to $SA..."
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA" \
  --role="roles/secretmanager.secretAccessor" --quiet

echo ""
echo "══════════════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  AR repo     : ${REGION}-docker.pkg.dev/${PROJECT}/wealthwatch"
echo "  Database    : Neon/Supabase (stored in Secret Manager)"
echo ""
echo "  Next: run  deploy/cloudrun/deploy.sh"
echo "══════════════════════════════════════════════════"
