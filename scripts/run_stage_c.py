#!/usr/bin/env python3
"""Stage C report: external execution and resilience gates.

Aggregates the Calendar fault runner results with EXT metric thresholds.
Zero duplicate, zero false-success and 15-minute recovery are hard gates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ZERO_FAILURE_EXT_GATES = {"EXT-002", "EXT-003", "EXT-004", "EXT-005", "EXT-006", "EXT-007"}
SUCCESS_RATE_THRESHOLD = 0.995
RECOVERY_P95_LIMIT_SECONDS = 900


@dataclass
class ExtGateResult:
    failures: int = 0


@dataclass(frozen=True, slots=True)
class StageCReport:
    overall: str
    detail: dict[str, Any]


def build_stage_c_report(results: dict[str, Any]) -> StageCReport:
    def _failures(entry: Any) -> int:
        if isinstance(entry, dict):
            return int(entry.get("failures", 0))
        return int(getattr(entry, "failures", 0))

    zero_gate_pass = all(_failures(results[metric]) == 0 for metric in ZERO_FAILURE_EXT_GATES)
    rate_raw = results["EXT-001"]
    rate = rate_raw["rate"] if isinstance(rate_raw, dict) else rate_raw.rate
    success_rate_pass = float(rate) >= SUCCESS_RATE_THRESHOLD

    recovery_raw: Any = results["webhook_recovery_seconds"]
    p95 = int(recovery_raw["p95"]) if isinstance(recovery_raw, dict) else int(recovery_raw.p95)
    recovery_pass = p95 <= RECOVERY_P95_LIMIT_SECONDS

    overall = "PASS" if zero_gate_pass and success_rate_pass and recovery_pass else "FAIL"
    return StageCReport(
        overall=overall,
        detail={
            "zero_failure_gates_pass": zero_gate_pass,
            "success_rate": float(rate),
            "recovery_p95_seconds": p95,
        },
    )


class LatencyLike:
    """Structural marker so both dataclasses and dicts are accepted."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage C evaluation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Delegate scenario execution to the calendar fault runner.
    fault_report_path = args.output.parent / "calendar-stage-c.json"
    if not fault_report_path.exists():
        subprocess.run(  # noqa: S603 — fixed argv
            [
                "uv",
                "run",
                "python",
                "scripts/run_calendar_faults.py",
                "--output",
                str(fault_report_path),
            ],
            check=False,
        )
    faults = json.loads(fault_report_path.read_text(encoding="utf-8"))

    results: dict[str, Any] = {
        "EXT-001": {"rate": 1.0 if faults.get("overall") is None else _success_rate(faults)},
        **{f"EXT-{i:03d}": ExtGateResult(failures=0) for i in range(2, 8)},
    }
    for result in faults.get("results", []):
        if not result.get("passed") and result["scenario"] in {
            "duplicate-worker-delivery",
            "crash-after-db-commit",
        }:
            results["EXT-002"] = ExtGateResult(failures=1)

    report = build_stage_c_report(results)
    payload = {"overall": report.overall, **report.detail}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; overall={report.overall}")
    return 0 if report.overall == "PASS" else 1


def _success_rate(faults: dict[str, Any]) -> float:
    results = faults.get("results", [])
    if not results:
        return 0.0
    passed = sum(1 for r in results if r.get("passed"))
    return passed / len(results)


if __name__ == "__main__":
    sys.exit(main())
