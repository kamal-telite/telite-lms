# Backup and Restore Runbook

## Purpose

Define the minimum operational backup and restore process for Telite LMS.

## Local Backup

Use:

```powershell
.\scripts\backup.ps1
```

The script captures:

- PostgreSQL databases.
- `.env`.
- Compose files.
- Uploads volume.
- Moodle data volume.

## Security Warning

Backup archives may contain secrets from `.env`.

Store archives only in encrypted storage with restricted access.

## Restore

Use:

```powershell
.\scripts\restore.ps1 -BackupArchive .\backups\telite_backup_<timestamp>.zip
```

## Restore Verification

Automated restore drill:

```text
.github/workflows/backup-restore-verification.yml
```

Local disposable verification:

```powershell
pwsh .github/scripts/verify-backup-restore.ps1
```

This creates two temporary Postgres containers, dumps source data, restores it into a target container, verifies restored data, and removes the containers.

## Production Requirements

Before production launch:

- Define RPO.
- Define RTO.
- Configure scheduled backups.
- Store backups off-host.
- Encrypt backup archives.
- Run restore drill at least weekly.
- Document the last successful restore.

## Minimum RPO/RTO Recommendation

Initial target:

- RPO: 24 hours
- RTO: 4 hours

Enterprise target:

- RPO: 15 minutes with WAL/PITR
- RTO: 1 hour

