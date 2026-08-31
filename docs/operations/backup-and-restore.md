# Backup and restore drill

The release gate accepts only a completed encrypted PostgreSQL restore into a separate, empty database. A Compose file or unit test alone is not restore evidence.

## Required inputs

- `--source-url`: source PostgreSQL connection URL.
- `--restore-url`: separate empty PostgreSQL database; the script rejects the source database as the target.
- `--backup-file`: a new output path. Existing files are never overwritten.
- `--now-utc`: explicit timezone-aware drill time, for example `2026-08-31T00:00:00+00:00`.
- `BACKUP_AGE_RECIPIENT`: age public recipient used to encrypt the dump.
- `BACKUP_AGE_IDENTITY`: age identity file used to decrypt the dump.

```bash
BACKUP_AGE_RECIPIENT='age1...' \
BACKUP_AGE_IDENTITY='/secure/path/identity.txt' \
uv run python scripts/test_backup_restore.py \
  --source-url "$SOURCE_DATABASE_URL" \
  --restore-url "$EMPTY_RESTORE_DATABASE_URL" \
  --backup-file '/secure/backups/pma-drill.sql.gz.age' \
  --now-utc '2026-08-31T00:00:00+00:00'
```

The command returns `0/PASS` only when plan snapshot and audit event counts match and the restored audit rows have no missing workspace, actor, or approval references. Missing database or age inputs return `2/BLOCKED_EXTERNAL`; dump, restore, query, count, or reference failures return `1/FAIL`.

Backups are encrypted before being committed to disk, written with owner-only permissions, and never overwrite an existing path. Restore drills must use an isolated empty database because the restore command intentionally does not clean or replace existing objects.

Production retention remains 30 days after primary deletion. Retention verification receives an explicit UTC observation time; it does not infer evidence from the machine clock. Quarterly staging restore drills and their immutable command output are required before release.
