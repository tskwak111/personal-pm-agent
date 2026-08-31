#!/usr/bin/env python3
"""Build Stage C only from complete fault-runner observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_METRICS = {
    "EXT-001",
    "EXT-002",
    "EXT-003",
    "EXT-004",
    "EXT-005",
    "EXT-006",
    "EXT-007",
    "webhook_recovery_seconds",
}
ZERO_FAILURE_EXT_GATES = {f"EXT-{index:03d}" for index in range(2, 8)}
SUCCESS_RATE_THRESHOLD = 0.995
RECOVERY_P95_LIMIT_SECONDS = 900


@dataclass
class ExtGateResult:
    failures: int = 0


@dataclass(frozen=True, slots=True)
class StageCReport:
    overall: str
    detail: dict[str, Any]


def _value(entry: Any, key: str) -> Any:
    return entry.get(key) if isinstance(entry, dict) else getattr(entry, key)


def build_stage_c_report(
    results: dict[str, Any],
    *,
    provider_profile: str = "emulator",
) -> StageCReport:
    missing = sorted(REQUIRED_METRICS - set(results))
    if missing:
        return StageCReport(
            "FAIL",
            {"missing_metrics": missing, "provider_profile": provider_profile},
        )
    if provider_profile not in {"emulator", "live"}:
        return StageCReport(
            "BLOCKED_EXTERNAL",
            {"missing_metrics": [], "provider_profile": provider_profile},
        )

    zero_gate_pass = all(
        int(_value(results[metric], "failures")) == 0 for metric in ZERO_FAILURE_EXT_GATES
    )
    rate = float(_value(results["EXT-001"], "rate"))
    p95 = int(_value(results["webhook_recovery_seconds"], "p95"))
    success_rate_pass = rate >= SUCCESS_RATE_THRESHOLD
    recovery_pass = p95 <= RECOVERY_P95_LIMIT_SECONDS
    overall = "PASS" if zero_gate_pass and success_rate_pass and recovery_pass else "FAIL"
    return StageCReport(
        overall,
        {
            "missing_metrics": [],
            "provider_profile": provider_profile,
            "zero_failure_gates_pass": zero_gate_pass,
            "success_rate": rate,
            "recovery_p95_seconds": p95,
        },
    )


def _failure_report(output: Path, reason: str) -> int:
    payload = {
        "schema_version": "1.0",
        "overall": "FAIL",
        "missing_metrics": sorted(REQUIRED_METRICS),
        "provider_profile": "none",
        "code_version": _revision(),
        "input_hash": hashlib.sha256(reason.encode()).hexdigest(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "metrics": {},
        "error": reason,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}; overall=FAIL")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage C evaluation")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("evals/fault-injection/calendar/scenarios.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="pma-stage-c-") as temporary:
        fault_report_path = Path(temporary) / "calendar-faults.json"
        process = subprocess.run(  # noqa: S603 - fixed local runner
            [
                sys.executable,
                str(ROOT / "scripts/run_calendar_faults.py"),
                "--scenarios",
                str(args.scenarios),
                "--output",
                str(fault_report_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0 or not fault_report_path.is_file():
            return _failure_report(args.output, (process.stdout + process.stderr)[-4000:])
        fault_bytes = fault_report_path.read_bytes()
        faults = json.loads(fault_bytes)

    metrics = faults.get("metrics")
    if not isinstance(metrics, dict):
        return _failure_report(args.output, "fault runner omitted metrics")
    report = build_stage_c_report(
        metrics,
        provider_profile=str(faults.get("provider_profile", "none")),
    )
    payload = {
        "schema_version": "1.0",
        "overall": report.overall,
        **report.detail,
        "code_version": _revision(),
        "input_hash": hashlib.sha256(fault_bytes).hexdigest(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "metrics": metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; overall={report.overall}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED_EXTERNAL": 2}[report.overall]


def _revision() -> str:
    result = subprocess.run(  # noqa: S603 - fixed git command
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


if __name__ == "__main__":
    sys.exit(main())
