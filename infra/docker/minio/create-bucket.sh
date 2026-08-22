#!/usr/bin/env sh
# Create the local S3-compatible bucket used for source artifacts.
set -eu

ENDPOINT="${S3_ENDPOINT:-http://localhost:9000}"
ACCESS_KEY="${S3_ACCESS_KEY_ID:-personal_pm}"
SECRET_KEY="${S3_SECRET_ACCESS_KEY:-local_only_password}"
BUCKET="${S3_BUCKET:-personal-pm-local}"

mc alias set local "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY"
mc mb --ignore-existing "local/$BUCKET"
echo "bucket ready: $BUCKET at $ENDPOINT"
