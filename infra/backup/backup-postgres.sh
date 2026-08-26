#!/usr/bin/env bash
# Encrypted nightly PostgreSQL backup (pg_dump | age-encrypted).
set -euo pipefail
: "${BACKUP_AGE_RECIPIENT:?set BACKUP_AGE_RECIPIENT}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="/backups/pma-${STAMP}.sql.gz.age"
pg_dump "${DATABASE_URL:?}" --no-owner --format=custom | gzip | age -r "$BACKUP_AGE_RECIPIENT" > "$OUT"
echo "wrote $OUT"
