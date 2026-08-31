#!/usr/bin/env bash
# Create one encrypted PostgreSQL custom-format dump.
set -euo pipefail
: "${BACKUP_AGE_RECIPIENT:?set BACKUP_AGE_RECIPIENT}"
: "${BACKUP_FILE:?set BACKUP_FILE}"
: "${BACKUP_NOW_UTC:?set BACKUP_NOW_UTC}"
: "${DATABASE_URL:?set DATABASE_URL}"
test ! -e "$BACKUP_FILE"
umask 077
PARTIAL="${BACKUP_FILE}.partial.$$"
trap 'rm -f "$PARTIAL"' EXIT
pg_dump "$DATABASE_URL" --no-owner --format=custom | gzip | age -r "$BACKUP_AGE_RECIPIENT" -o "$PARTIAL"
mv "$PARTIAL" "$BACKUP_FILE"
trap - EXIT
echo "wrote $BACKUP_FILE at $BACKUP_NOW_UTC"
