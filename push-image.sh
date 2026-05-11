#!/usr/bin/env bash
# =============================================================================
# push-image.sh — Build, tag, and push the Telite LMS Moodle image to GHCR
#
# Prerequisites:
#   1. Docker Desktop running
#   2. A .env file with GHCR_USERNAME and GHCR_TOKEN set
#   3. The GitHub PAT must have  write:packages  scope
#
# Usage:
#   chmod +x push-image.sh
#   ./push-image.sh              # pushes :latest
#   ./push-image.sh v1.2.0       # pushes :v1.2.0 AND :latest
# =============================================================================

set -euo pipefail

# ── Load .env ────────────────────────────────────────────────────────────────
if [ -f .env ]; then
    # Export only lines that look like VAR=VALUE (skip comments and blanks)
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
else
    echo "ERROR: .env file not found. Copy .env.example to .env and fill it in."
    exit 1
fi

# ── Validate required variables ──────────────────────────────────────────────
if [ -z "${GHCR_USERNAME:-}" ]; then
    echo "ERROR: GHCR_USERNAME is not set in .env"
    exit 1
fi
if [ -z "${GHCR_TOKEN:-}" ]; then
    echo "ERROR: GHCR_TOKEN is not set in .env"
    exit 1
fi

# ── Configuration ────────────────────────────────────────────────────────────
IMAGE_NAME="ghcr.io/${GHCR_USERNAME}/telite-lms-moodle"
TAG="${1:-latest}"

echo "============================================="
echo "  Telite LMS — Image Push to GHCR"
echo "============================================="
echo "  Image:  ${IMAGE_NAME}"
echo "  Tag:    ${TAG}"
echo "============================================="
echo ""

# ── Step 1: Authenticate with GHCR ──────────────────────────────────────────
echo "→ Logging in to ghcr.io..."
echo "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USERNAME}" --password-stdin
echo ""

# ── Step 2: Build the image ──────────────────────────────────────────────────
echo "→ Building image: ${IMAGE_NAME}:${TAG} ..."
docker build -t "${IMAGE_NAME}:${TAG}" .

# Also tag as :latest if a custom tag was provided
if [ "${TAG}" != "latest" ]; then
    echo "→ Also tagging as :latest ..."
    docker tag "${IMAGE_NAME}:${TAG}" "${IMAGE_NAME}:latest"
fi
echo ""

# ── Step 3: Push to GHCR ────────────────────────────────────────────────────
echo "→ Pushing ${IMAGE_NAME}:${TAG} ..."
docker push "${IMAGE_NAME}:${TAG}"

if [ "${TAG}" != "latest" ]; then
    echo "→ Pushing ${IMAGE_NAME}:latest ..."
    docker push "${IMAGE_NAME}:latest"
fi

echo ""
echo "============================================="
echo "  ✅ Done! Image pushed successfully."
echo ""
echo "  Your teammate can now pull it:"
echo "    docker pull ${IMAGE_NAME}:latest"
echo "============================================="
