-- Local development database bootstrap.
-- Schema evolution is owned by Alembic migrations (Phase 3); this file only
-- prepares extensions that must exist before the first migration runs.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
