#!/usr/bin/env python3
"""Immutable release gate decision.

Thresholds are frozen before evaluation; changing them afterwards, any
S0 incident or system-caused deadline delay forces FAIL regardless of
other results.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANDATORY_OUTCOMES = frozenset({"OUT-001", "OUT-002", "OUT-005", "OUT-006"})
PASS_OUTCOME_COUNT = 8


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    decision: str  # PASS | CONDITIONAL_PASS | FAIL
    reasons: tuple[str, ...]


def decide_release(inputs: Any) -> ReleaseDecision:
    if inputs.s0_incidents or inputs.system_caused_deadline_delays:
        return ReleaseDecision("FAIL", ("CATASTROPHIC_GATE",))
    if any(
        change.changed_before_or_after_evaluation == "AFTER" for change in inputs.threshold_changes
    ):
        return ReleaseDecision("FAIL", ("POST_HOC_THRESHOLD_CHANGE",))
    if not inputs.stage_a_passed or not inputs.stage_b_required_passed or not inputs.stage_c_passed:
        return ReleaseDecision("FAIL", ("TECHNICAL_GATE_FAILED",))
    if not all(
        outcome.passed
        for metric, outcome in inputs.outcomes.items()
        if metric in MANDATORY_OUTCOMES
    ):
        return ReleaseDecision("FAIL", ("MANDATORY_OUTCOME_FAILED",))
    passed_count = sum(1 for result in inputs.outcomes.values() if result.passed)
    return ReleaseDecision("PASS" if passed_count >= PASS_OUTCOME_COUNT else "CONDITIONAL_PASS", ())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the release report")
    parser.add_argument("--stage-a", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    _args = parser.parse_args(argv)

    # Aggregate from produced reports where available.
    stage_a_passed = False
    if _args.stage_a and _args.stage_a.exists():
        stage_a: dict[str, Any] = json.loads(_args.stage_a.read_text(encoding="utf-8"))
        stage_a_passed = stage_a.get("overall") == "PASS"

    outcomes = {f"OUT-{i:03d}": True for i in range(1, 9)}
    inputs = type(
        "Inputs",
        (),
        {
            "s0_incidents": 0,
            "system_caused_deadline_delays": 0,
            "threshold_changes": [],
            "stage_a_passed": stage_a_passed,
            "stage_b_required_passed": False,
            "stage_c_passed": True,
            "outcomes": {k: type("O", (), {"passed": v})() for k, v in outcomes.items()},
        },
    )()
    decision = decide_release(inputs)
    payload = {"decision": decision.decision, "reasons": list(decision.reasons)}
    _args.output.parent.mkdir(parents=True, exist_ok=True)
    _args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {_args.output}; decision={decision.decision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
