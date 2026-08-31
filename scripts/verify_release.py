#!/usr/bin/env python3
"""Decide release only from complete, hashed evaluation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

MANDATORY_OUTCOMES = frozenset({"OUT-001", "OUT-002", "OUT-005", "OUT-006"})
REQUIRED_OUTCOMES = frozenset(f"OUT-{index:03d}" for index in range(1, 11))
INPUT_NAMES = (
    "stage-a",
    "stage-b",
    "stage-c",
    "outcomes",
    "incidents",
    "threshold-changes",
)


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    decision: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OutcomeResult:
    passed: bool
    within_ten_percent: bool


@dataclass(frozen=True, slots=True)
class ThresholdChange:
    changed_before_or_after_evaluation: str


@dataclass(frozen=True, slots=True)
class ReleaseInputs:
    s0_incidents: int
    system_caused_deadline_delays: int
    threshold_changes: tuple[ThresholdChange, ...]
    stage_a_passed: bool
    stage_b_required_passed: bool
    stage_c_passed: bool
    external_evidence_blocked: bool
    outcomes: dict[str, OutcomeResult]
    reevaluation_date: str | None


def decide_release(inputs: Any) -> ReleaseDecision:
    if inputs.s0_incidents or inputs.system_caused_deadline_delays:
        return ReleaseDecision("FAIL", ("CATASTROPHIC_GATE",))
    if any(
        change.changed_before_or_after_evaluation == "AFTER" for change in inputs.threshold_changes
    ):
        return ReleaseDecision("FAIL", ("POST_HOC_THRESHOLD_CHANGE",))
    if getattr(inputs, "external_evidence_blocked", False):
        return ReleaseDecision("FAIL", ("EXTERNAL_EVIDENCE_BLOCKED",))
    if not inputs.stage_a_passed or not inputs.stage_b_required_passed or not inputs.stage_c_passed:
        return ReleaseDecision("FAIL", ("TECHNICAL_GATE_FAILED",))

    missing = REQUIRED_OUTCOMES - set(inputs.outcomes)
    if missing:
        return ReleaseDecision("FAIL", ("MISSING_OUTCOME",))
    if any(not inputs.outcomes[metric].passed for metric in MANDATORY_OUTCOMES):
        return ReleaseDecision("FAIL", ("MANDATORY_OUTCOME_FAILED",))

    optional_failures = [
        inputs.outcomes[metric]
        for metric in REQUIRED_OUTCOMES - MANDATORY_OUTCOMES
        if not inputs.outcomes[metric].passed
    ]
    if not optional_failures:
        return ReleaseDecision("PASS", ())
    if (
        len(optional_failures) == 1
        and optional_failures[0].within_ten_percent
        and getattr(inputs, "reevaluation_date", None)
    ):
        return ReleaseDecision("CONDITIONAL_PASS", ("ONE_OPTIONAL_OUTCOME_NEAR_THRESHOLD",))
    return ReleaseDecision("FAIL", ("OUTCOME_GATE_FAILED",))


def _load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw_bytes = path.read_bytes()
    value = json.loads(raw_bytes)
    if not isinstance(value, dict):
        raise ValueError(f"input must be a JSON object: {path}")
    if value.get("schema_version") != "1.0":
        raise ValueError(f"unsupported or missing schema_version: {path}")
    return value, raw_bytes


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _parse_outcomes(value: dict[str, Any]) -> tuple[dict[str, OutcomeResult], str | None]:
    raw_outcomes = value.get("outcomes")
    if not isinstance(raw_outcomes, dict):
        raise ValueError("outcomes must be an object")
    outcomes: dict[str, OutcomeResult] = {}
    for metric, raw in raw_outcomes.items():
        if not isinstance(metric, str) or not isinstance(raw, dict):
            raise ValueError("each outcome must be an object")
        passed = raw.get("passed")
        within = raw.get("within_ten_percent", False)
        if not isinstance(passed, bool) or not isinstance(within, bool):
            raise ValueError(f"invalid outcome flags: {metric}")
        outcomes[metric] = OutcomeResult(passed=passed, within_ten_percent=within)
    reevaluation_date = value.get("reevaluation_date")
    if reevaluation_date is not None:
        if not isinstance(reevaluation_date, str):
            raise ValueError("reevaluation_date must be an ISO date or null")
        date.fromisoformat(reevaluation_date)
    return outcomes, reevaluation_date


def _parse_changes(value: dict[str, Any]) -> tuple[ThresholdChange, ...]:
    raw_changes = value.get("changes")
    if not isinstance(raw_changes, list):
        raise ValueError("threshold changes must be an array")
    changes: list[ThresholdChange] = []
    for raw in raw_changes:
        if not isinstance(raw, dict):
            raise ValueError("threshold change must be an object")
        timing = raw.get("changed_before_or_after_evaluation")
        if timing not in {"BEFORE", "AFTER"}:
            raise ValueError("threshold change timing must be BEFORE or AFTER")
        changes.append(ThresholdChange(str(timing)))
    return tuple(changes)


def _revision() -> str:
    result = subprocess.run(  # noqa: S603 - fixed git command
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _write_report(
    output: Path,
    decision: ReleaseDecision,
    *,
    input_hashes: dict[str, str],
    error: str | None = None,
) -> None:
    payload = {
        "schema_version": "1.0",
        "decision": decision.decision,
        "reasons": list(decision.reasons),
        "input_hashes": input_hashes,
        "code_version": _revision(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "error": error,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output}; decision={decision.decision}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the immutable release report")
    for name in INPUT_NAMES:
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    paths = {name: getattr(args, name.replace("-", "_")) for name in INPUT_NAMES}
    missing = sorted(name for name, path in paths.items() if path is None or not path.is_file())
    if missing:
        decision = ReleaseDecision("FAIL", ("INPUT_MISSING",))
        _write_report(args.output, decision, input_hashes={}, error=",".join(missing))
        return 1

    try:
        loaded = {name: _load(path) for name, path in paths.items() if path is not None}
        values = {name: item[0] for name, item in loaded.items()}
        hashes = {name: hashlib.sha256(item[1]).hexdigest() for name, item in loaded.items()}
        statuses = {name: values[name].get("overall") for name in ("stage-a", "stage-b", "stage-c")}
        for name, status in statuses.items():
            if status not in {"PASS", "FAIL", "BLOCKED_EXTERNAL"}:
                raise ValueError(f"invalid {name} overall status")
        stage_c_profile = values["stage-c"].get("provider_profile")
        if stage_c_profile not in {"emulator", "live", "none"}:
            raise ValueError("invalid stage-c provider_profile")
        outcomes, reevaluation_date = _parse_outcomes(values["outcomes"])
        incidents = values["incidents"]
        release_inputs = ReleaseInputs(
            s0_incidents=_nonnegative_int(incidents.get("s0_incidents"), "s0_incidents"),
            system_caused_deadline_delays=_nonnegative_int(
                incidents.get("system_caused_deadline_delays"),
                "system_caused_deadline_delays",
            ),
            threshold_changes=_parse_changes(values["threshold-changes"]),
            stage_a_passed=statuses["stage-a"] == "PASS",
            stage_b_required_passed=statuses["stage-b"] == "PASS",
            stage_c_passed=statuses["stage-c"] == "PASS",
            external_evidence_blocked=(
                "BLOCKED_EXTERNAL" in statuses.values() or stage_c_profile != "live"
            ),
            outcomes=outcomes,
            reevaluation_date=reevaluation_date,
        )
        decision = decide_release(release_inputs)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        _write_report(
            args.output,
            ReleaseDecision("FAIL", ("INPUT_INVALID",)),
            input_hashes={},
            error=str(error),
        )
        return 1

    _write_report(args.output, decision, input_hashes=hashes)
    return {"PASS": 0, "FAIL": 1, "CONDITIONAL_PASS": 2}[decision.decision]


if __name__ == "__main__":
    sys.exit(main())
