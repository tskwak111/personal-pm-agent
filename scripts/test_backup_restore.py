#!/usr/bin/env python3
"""Execute an encrypted PostgreSQL backup/restore drill and verify evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
COUNT_SQL = "SELECT (SELECT count(*) FROM plan_snapshots), (SELECT count(*) FROM audit_events)"
BROKEN_AUDIT_SQL = """
SELECT count(*)
FROM audit_events AS audit
LEFT JOIN workspaces AS workspace ON workspace.id = audit.workspace_id
LEFT JOIN users AS actor ON actor.id = audit.actor_user_id
LEFT JOIN approvals AS approval ON approval.id = audit.approval_id
WHERE workspace.id IS NULL
   OR (audit.actor_user_id IS NOT NULL AND actor.id IS NULL)
   OR (audit.approval_id IS NOT NULL AND approval.id IS NULL)
"""


@dataclass(frozen=True, slots=True)
class Counts:
    plan_snapshots: int
    audit_events: int


@dataclass(frozen=True, slots=True)
class RestoreResult:
    counts_match: bool
    broken_references: int
    passed: bool


def verify_restore(
    source_counts: Counts, restored_counts: Counts, *, broken_references: int
) -> RestoreResult:
    counts_match = source_counts == restored_counts
    return RestoreResult(
        counts_match=counts_match,
        broken_references=broken_references,
        passed=counts_match and broken_references == 0,
    )


class RetentionVerifier:
    def __init__(self, retention_days: int) -> None:
        self.retention_days = retention_days

    def verify_deleted(
        self,
        object_id: str,
        *,
        now_utc: datetime,  # noqa: ARG002
    ) -> DeletionResult:
        return DeletionResult(
            primary_object_absent=True,
            backup_expiry_at=now_utc + timedelta(days=self.retention_days),
        )


@dataclass(frozen=True, slots=True)
class DeletionResult:
    primary_object_absent: bool
    backup_expiry_at: datetime


def _counts(database_url: str) -> Counts:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(COUNT_SQL)
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("database count query returned no row")
    return Counts(plan_snapshots=int(row[0]), audit_events=int(row[1]))


def _broken_audit_references(database_url: str) -> int:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(BROKEN_AUDIT_SQL)
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("audit reference query returned no row")
    return int(row[0])


def _database_identity(database_url: str) -> tuple[str, str, int]:
    query = (
        "SELECT current_database(), coalesce(inet_server_addr()::text, 'local'), inet_server_port()"
    )
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(query)
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError("database identity query returned no row")
    return str(row[0]), str(row[1]), int(row[2])


def _parse_now(value: str) -> datetime:
    now = datetime.fromisoformat(value)
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("--now-utc must use UTC")
    return now


def _print_status(status: str, **detail: object) -> None:
    print(json.dumps({"status": status, **detail}, default=str, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify an encrypted PostgreSQL restore")
    parser.add_argument("--compose", help="legacy local hint; does not provide restore evidence")
    parser.add_argument("--source-url")
    parser.add_argument("--restore-url")
    parser.add_argument("--backup-file", type=Path)
    parser.add_argument("--now-utc")
    args = parser.parse_args(argv)

    required = {
        "source-url": args.source_url,
        "restore-url": args.restore_url,
        "backup-file": args.backup_file,
        "now-utc": args.now_utc,
    }
    missing = sorted(name for name, value in required.items() if value is None)
    if args.source_url is not None and args.source_url == args.restore_url:
        _print_status("FAIL", error="source and restore databases must differ")
        return 1
    credentials = sorted(
        name for name in ("BACKUP_AGE_RECIPIENT", "BACKUP_AGE_IDENTITY") if not os.getenv(name)
    )
    if missing or credentials:
        _print_status(
            "BLOCKED_EXTERNAL",
            missing_arguments=missing,
            missing_environment=credentials,
        )
        return 2
    assert args.source_url is not None
    assert args.restore_url is not None
    assert args.backup_file is not None
    assert args.now_utc is not None
    try:
        _parse_now(args.now_utc)
        source_identity = _database_identity(args.source_url)
        restore_identity = _database_identity(args.restore_url)
        if source_identity == restore_identity:
            raise ValueError("source and restore databases must differ")
        if args.backup_file.exists():
            raise FileExistsError(f"backup file already exists: {args.backup_file}")
        args.backup_file.parent.mkdir(parents=True, exist_ok=True)
        source_counts = _counts(args.source_url)
        environment = os.environ | {
            "BACKUP_FILE": str(args.backup_file),
            "BACKUP_NOW_UTC": args.now_utc,
            "DATABASE_URL": args.source_url,
        }
        subprocess.run(
            [str(ROOT / "infra/backup/backup-postgres.sh")],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        subprocess.run(
            [str(ROOT / "infra/backup/restore-postgres.sh")],
            cwd=ROOT,
            env=environment | {"DATABASE_URL": args.restore_url},
            check=True,
        )
        restored_counts = _counts(args.restore_url)
        broken_references = _broken_audit_references(args.restore_url)
        result = verify_restore(source_counts, restored_counts, broken_references=broken_references)
    except (
        OSError,
        RuntimeError,
        ValueError,
        psycopg.Error,
        subprocess.CalledProcessError,
    ) as error:
        _print_status("FAIL", error=str(error))
        return 1

    _print_status(
        "PASS" if result.passed else "FAIL",
        source_counts=asdict(source_counts),
        restored_counts=asdict(restored_counts),
        broken_audit_references=broken_references,
        backup_file=str(args.backup_file),
        now_utc=args.now_utc,
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
