# Production Hardening Implementation Plan

Date: 2026-06-23

## Phase P0 - Repository Stabilization

Deliverables:

- Production baseline document.
- Worktree stabilization audit.
- Confirm ignored local artifacts stay local.

Status:

- Implemented.

## Phase P1 - CI Reliability Expansion

Deliverables:

- Expand backend critical regression gate.
- Run frontend unit tests before build.
- Add CI timeouts.
- Upload JUnit test artifacts on failure.
- Keep live/browser tests opt-in.

Status:

- Implemented in `.github/workflows/ci.yml`.

## Phase P2 - Release Supply Chain Hardening

Deliverables:

- Build release images.
- Scan images with Trivy.
- Generate SBOMs.
- Upload SBOM artifacts.
- Push versioned images to GHCR.
- Enable provenance.
- Sign images with Cosign keyless signing.

Status:

- Implemented in `.github/workflows/container-release.yml`.

## Phase P3 - Deployment Promotion

Deliverables:

- Staging deployment workflow.
- Production deployment workflow.
- Manual environment approval via GitHub Environments.
- Immutable image digest/tag inputs.
- Post-deploy smoke tests.

Status:

- Implemented in `.github/workflows/deploy.yml`.

## Phase P4 - Backup and Restore Verification

Deliverables:

- Restore verification workflow.
- Backup and restore runbook.
- Verification script.

Status:

- Implemented in `.github/workflows/backup-restore-verification.yml`.
- Implemented in `.github/scripts/verify-backup-restore.ps1`.
- Documented in `docs/production/backup-restore-runbook.md`.

## Phase P5 - Observability Hardening

Deliverables:

- Prometheus scrape configuration.
- Alert rules.
- Grafana dashboard starter.
- Observability runbook.

Status:

- Implemented under `docker/observability/`.
- Documented in `docs/production/observability-runbook.md`.

## Phase P6 - Production Runbooks

Deliverables:

- Deployment runbook.
- Rollback runbook.
- Backup and restore runbook.
- Observability runbook.
- Incident response runbook.

Status:

- Implemented under `docs/production/`.

