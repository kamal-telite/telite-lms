# =============================================================================
# push-image.ps1 — Build, tag, and push the Telite LMS Moodle image to GHCR
#
# Windows PowerShell equivalent of push-image.sh
#
# Prerequisites:
#   1. Docker Desktop running
#   2. A .env file with GHCR_USERNAME and GHCR_TOKEN set
#   3. The GitHub PAT must have  write:packages  scope
#
# Usage:
#   .\push-image.ps1              # pushes :latest
#   .\push-image.ps1 v1.2.0      # pushes :v1.2.0 AND :latest
# =============================================================================

param(
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

# ── Load .env ────────────────────────────────────────────────────────────────
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
} else {
    Write-Error "ERROR: .env file not found. Copy .env.example to .env and fill it in."
    exit 1
}

# ── Validate required variables ──────────────────────────────────────────────
$GhcrUsername = $env:GHCR_USERNAME
$GhcrToken   = $env:GHCR_TOKEN

if ([string]::IsNullOrEmpty($GhcrUsername)) {
    Write-Error "ERROR: GHCR_USERNAME is not set in .env"
    exit 1
}
if ([string]::IsNullOrEmpty($GhcrToken)) {
    Write-Error "ERROR: GHCR_TOKEN is not set in .env"
    exit 1
}

# ── Configuration ────────────────────────────────────────────────────────────
$ImageName = "ghcr.io/$GhcrUsername/telite-lms-moodle"

Write-Host "============================================="
Write-Host "  Telite LMS - Image Push to GHCR"
Write-Host "============================================="
Write-Host "  Image:  $ImageName"
Write-Host "  Tag:    $Tag"
Write-Host "============================================="
Write-Host ""

# ── Step 1: Authenticate with GHCR ──────────────────────────────────────────
Write-Host "-> Logging in to ghcr.io..."
$GhcrToken | docker login ghcr.io -u $GhcrUsername --password-stdin
Write-Host ""

# ── Step 2: Build the image ──────────────────────────────────────────────────
Write-Host "-> Building image: ${ImageName}:${Tag} ..."
docker build -t "${ImageName}:${Tag}" .

if ($Tag -ne "latest") {
    Write-Host "-> Also tagging as :latest ..."
    docker tag "${ImageName}:${Tag}" "${ImageName}:latest"
}
Write-Host ""

# ── Step 3: Push to GHCR ────────────────────────────────────────────────────
Write-Host "-> Pushing ${ImageName}:${Tag} ..."
docker push "${ImageName}:${Tag}"

if ($Tag -ne "latest") {
    Write-Host "-> Pushing ${ImageName}:latest ..."
    docker push "${ImageName}:latest"
}

Write-Host ""
Write-Host "============================================="
Write-Host "  Done! Image pushed successfully."
Write-Host ""
Write-Host "  Your teammate can now pull it:"
Write-Host "    docker pull ${ImageName}:latest"
Write-Host "============================================="
