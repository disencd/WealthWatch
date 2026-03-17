#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# WealthWatch — Deploy frontend to Firebase Hosting
#
# Usage:
#   export VITE_API_BASE=https://wealthwatch-api-xxxxx-uc.a.run.app/api/v1
#   bash deploy/cloudrun/deploy-frontend.sh
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Build frontend ───────────────────────────────────────────────────
echo "→ Building SvelteKit frontend..."
cd "$ROOT_DIR/frontend"
npm ci
npm run build

echo "→ Copying firebase.json..."
cp "$SCRIPT_DIR/firebase.json" "$ROOT_DIR/frontend/firebase.json"

# ── Deploy to Firebase Hosting ───────────────────────────────────────
echo "→ Deploying to Firebase Hosting..."
cd "$ROOT_DIR/frontend"
npx firebase-tools deploy --only hosting

echo ""
echo "══════════════════════════════════════════════════"
echo "  Frontend deployed to Firebase Hosting!"
echo "══════════════════════════════════════════════════"
