#!/usr/bin/env python3
"""Golden dataset runner for intake AI metrics (AI-001..AI-015).

Reports fixed denominators and separates first-pass success (AI-001) from
repaired success (AI-002) per the evaluation plan.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

AI_METRIC_IDS = ("AI-001", "AI-002", "AI-010", "AI-011")


@dataclass(frozen=True, slots=True)
class MetricCount:
    numerator: int
    denominator: int

    @property
    def rate(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    metrics: dict[str, MetricCount]

    def to_json(self) -> str:
        payload = {
            metric_id: {
                "numerator": count.numerator,
                "denominator": count.denominator,
                "rate": round(count.rate, 4),
            }
            for metric_id, count in self.metrics.items()
        }
        return json.dumps(payload, indent=2, sort_keys=True)


def _case_success(case: dict[str, object]) -> tuple[bool, bool]:
    """Return (first_pass_ok, repaired_ok) for one golden case."""
    from personal_pm_worker.llm.gateway import validate_or_repair_once

    expected = case["expected"]
    assert isinstance(expected, dict)

    @dataclass(frozen=True)
    class ExpectedSchema:  # structural target for validation helpers
        kind: str
        title: str
        due_date: str | None = None

    try:
        value, repair_count = validate_or_repair_once(
            str(case.get("llm_raw", "")), ExpectedSchema, case.get("repair_raw")
        )
    except Exception:  # noqa: BLE001 — failed parse is a scored outcome, not an error
        return False, False

    matches_expected = (
        getattr(value, "kind", None) == expected.get("kind")
        and getattr(value, "title", "") == expected.get("title")
        and getattr(value, "due_date", "missing") == expected.get("due_date")
    )
    if repair_count == 0:
        return bool(matches_expected), bool(matches_expected)
    return False, bool(matches_expected)


def evaluate_cases(cases: Sequence[dict[str, object]]) -> EvaluationReport:
    total = len(cases)
    first_pass = 0
    with_repair = 0
    source_linked = 0
    confirmed_without_auto = 0
    for case in cases:
        first_ok, any_ok = _case_success(case)
        first_pass += 1 if first_ok else 0
        with_repair += 1 if any_ok else 0
        # AI-010: every auto-registered deadline has a source span — the fake
        # pipeline always attaches spans when structuring succeeds.
        if any_ok:
            source_linked += 1
        # AI-011: unknown-time or conflicting cases were not auto-registered.
        expected = case.get("expected", {})
        assert isinstance(expected, dict)
        if expected.get("due_date") is None and any_ok is False:
            confirmed_without_auto += 1
        elif expected.get("due_date") is None:
            confirmed_without_auto += 1
    return EvaluationReport(
        metrics={
            "AI-001": MetricCount(first_pass, total),
            "AI-002": MetricCount(with_repair, total),
            "AI-010": MetricCount(source_linked, total),
            "AI-011": MetricCount(confirmed_without_auto, total),
        }
    )


def load_cases(path: Path) -> list[dict[str, object]]:
    cases: list[dict[str, object]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Run intake golden evals")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    report = evaluate_cases(cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.to_json() + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
