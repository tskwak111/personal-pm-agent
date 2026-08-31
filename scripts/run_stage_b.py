#!/usr/bin/env python3
"""Fail-closed Stage B corpus and metric gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REQUIRED_THRESHOLDS = {
    "AI-001": ("min", 0.985),
    "AI-002": ("min", 0.995),
    "AI-003": ("min", 1.000),
    "AI-004": ("max", 0.000),
    "AI-005": ("max", 0.000),
    "AI-010": ("min", 0.990),
    "AI-011": ("min", 0.950),
    "AI-012": ("min", 0.995),
    "AI-013": ("min", 0.980),
    "AI-014": ("max", 0.000),
    "AI-015": ("min", 1.000),
    "PQ-RISK-MACRO-F1": ("min", 0.900),
    "PQ-P0-P1-RECALL": ("min", 0.980),
    "PQ-AUTH-ACCURACY": ("min", 1.000),
    "PQ-UNREALISTIC-PLANS": ("max", 0.000),
}
MIN_GOLDEN_SOURCES = 200
MIN_EXPERT_SCENARIOS = 150


@dataclass(frozen=True, slots=True)
class PrecisionRecall:
    precision: float
    recall: float


def compute_precision_recall(
    *, true_positive: int, false_positive: int, false_negative: int
) -> PrecisionRecall:
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    return PrecisionRecall(precision=precision, recall=recall)


@dataclass(frozen=True, slots=True)
class StageBReport:
    overall: str
    metrics: dict[str, dict[str, object]]
    denominators: dict[str, int]


def build_stage_b_report(
    counts: dict[str, float],
    *,
    golden_count: int,
    expert_count: int,
) -> StageBReport:
    metrics: dict[str, dict[str, object]] = {}
    any_failure = False
    for metric_id, (direction, threshold) in REQUIRED_THRESHOLDS.items():
        value = counts.get(metric_id)
        if value is None:
            metrics[metric_id] = {
                "value": None,
                "threshold": threshold,
                "direction": direction,
                "status": "MISSING",
                "passed": False,
            }
            any_failure = True
            continue
        passed = value >= threshold if direction == "min" else value <= threshold
        metrics[metric_id] = {
            "value": value,
            "threshold": threshold,
            "direction": direction,
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
        }
        any_failure = any_failure or not passed

    denominators = {
        "golden_sources": golden_count,
        "expert_scenarios": expert_count,
    }
    if golden_count < MIN_GOLDEN_SOURCES or expert_count < MIN_EXPERT_SCENARIOS:
        overall = "BLOCKED_EXTERNAL"
    else:
        overall = "FAIL" if any_failure else "PASS"
    return StageBReport(overall=overall, metrics=metrics, denominators=denominators)


class DatasetError(ValueError):
    pass


def count_jsonl_records(directory: Path, *, id_fields: tuple[str, ...]) -> int:
    seen: set[str] = set()
    count = 0
    for path in sorted(directory.rglob("*.jsonl")) if directory.is_dir() else ():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                raise DatasetError(f"malformed JSONL: {path}:{line_number}") from error
            if not isinstance(item, dict):
                raise DatasetError(f"JSONL record must be an object: {path}:{line_number}")
            record_id = next(
                (
                    item[field]
                    for field in id_fields
                    if isinstance(item.get(field), str) and item[field]
                ),
                None,
            )
            if not isinstance(record_id, str):
                raise DatasetError(f"JSONL record is missing an ID: {path}:{line_number}")
            if record_id in seen:
                raise DatasetError(f"duplicate dataset ID: {record_id}")
            seen.add(record_id)
            count += 1
    return count


def _load_counts(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DatasetError("counts.json must be an object")
    result: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DatasetError(f"metric value must be numeric: {key}")
        result[str(key)] = float(value)
    return result


def _input_hash(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path).encode())
        digest.update(b"\0")
        if path.is_file():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _revision() -> str:
    result = subprocess.run(  # noqa: S603 - fixed git command
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage B evaluation")
    parser.add_argument("--golden", type=Path, default=Path("evals/golden"))
    parser.add_argument("--expert", type=Path, default=Path("evals/expert-scenarios"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    counts_path = args.golden / "counts.json"
    files = tuple(args.golden.rglob("*.jsonl")) + tuple(args.expert.rglob("*.jsonl"))

    error: str | None = None
    try:
        golden_count = count_jsonl_records(args.golden, id_fields=("case_id",))
        expert_count = count_jsonl_records(args.expert, id_fields=("scenario_id", "case_id"))
        counts = _load_counts(counts_path)
        report = build_stage_b_report(
            counts,
            golden_count=golden_count,
            expert_count=expert_count,
        )
    except (DatasetError, json.JSONDecodeError) as exception:
        error = str(exception)
        report = StageBReport(
            overall="FAIL",
            metrics={},
            denominators={"golden_sources": 0, "expert_scenarios": 0},
        )

    payload = {
        "schema_version": "1.0",
        "overall": report.overall,
        "metrics": report.metrics,
        "denominators": report.denominators,
        "code_version": _revision(),
        "input_hash": _input_hash((*files, counts_path)),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "error": error,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; overall={report.overall}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED_EXTERNAL": 2}[report.overall]


if __name__ == "__main__":
    sys.exit(main())
