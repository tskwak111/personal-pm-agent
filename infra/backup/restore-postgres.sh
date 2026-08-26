#!/usr/bin/env bash
# Point-in-time-compatible restore from an encrypted dump.
set -euo pipefail
: "${BACKUP_FILE:?set BACKUP_FILE}"
: "${BACKUP_AGE_IDENTITY:?set BACKUP_AGE_IDENTITY}"
age -d -i "$BACKUP_AGE_IDENTITY" < "$BACKUP_FILE" | gunzip | pg_restore --no-owner --dbname "${DATABASE_URL:?}"
echo "restored $BACKUP_FILE"
