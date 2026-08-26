#!/usr/bin/env python3
"""Stage B quality metrics: golden + expert scenario evaluation.

Thresholds are frozen from the evaluation plan and can never be weakened
in code.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_THRESHOLDS = {
    "AI-001": 0.985,
    "AI-002": 0.995,
    "AI-010": 0.990,
    "AI-011": 0.950,
    "AI-012": 0.995,
    "AI-013": 0.980,
    "PQ-RISK-MACRO-F1": 0.900,
    "PQ-P0-P1-RECALL": 0.980,
    "PQ-AUTH-ACCURACY": 1.000,
}


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


def build_stage_b_report(counts: dict[str, float]) -> StageBReport:
    metrics: dict[str, dict[str, object]] = {}
    all_pass = True
    for metric_id, threshold in REQUIRED_THRESHOLDS.items():
        value = counts.get(metric_id, 0.0)
        passed = value >= threshold
        all_pass = all_pass and passed
        metrics[metric_id] = {"value": value, "threshold": threshold, "passed": passed}
    return StageBReport(overall="PASS" if all_pass else "FAIL", metrics=metrics)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Stage B evaluation")
    parser.add_argument("--golden", type=Path, default=Path("evals/golden"))
    parser.add_argument("--expert", type=Path, default=Path("evals/expert-scenarios"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Metric values are produced by the intake eval runner; thresholds here.
    counts_path = args.golden / "counts.json"
    if counts_path.exists():
        counts = json.loads(counts_path.read_text(encoding="utf-8"))
    else:
        print(f"warning: {counts_path} missing; reporting FAIL", file=sys.stderr)
        counts = {}

    report = build_stage_b_report({k: float(v) for k, v in counts.items()})
    payload = {
        "overall": report.overall,
        "metrics": report.metrics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; overall={report.overall}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
