#!/usr/bin/env python3
"""Stage C fault-injection gate runner for Calendar execution.

Simulates each required failure scenario against the deterministic fake
adapter and reports EXT metric failures. Zero duplicates and zero false
successes are hard gates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_SCENARIOS = (
    "api-timeout",
    "rate-limit-429",
    "provider-5xx",
    "oauth-expired",
    "duplicate-worker-delivery",
    "crash-after-db-commit",
    "provider-success-response-lost",
)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class FaultReport:
    results: tuple[ScenarioResult, ...]
    metrics: dict[str, Any]
    total: int


class _ScenarioAdapter:
    """Fake provider adapter with per-scenario fault behaviour."""

    def __init__(self, scenario: str = "") -> None:
        self.scenario = scenario
        self.create_calls = 0
        self.events_by_key: dict[str, str] = {}
        self.reauth_required = False
        self._response_lost = False

    async def execute(self, command: dict[str, object]) -> dict[str, object]:
        key = str(command["idempotency_key"])
        if self.reauth_required:
            from personal_pm_worker.calendar.repository import PermanentFailureError

            raise PermanentFailureError("invalid_grant")
        if key in self.events_by_key:
            return {"external_event_id": self.events_by_key[key], "created": False}
        if (
            self.scenario in ("api-timeout", "provider-success-response-lost")
            and not self._response_lost
        ):
            # Provider commits, then the response is lost.
            self._response_lost = True
            self.create_calls += 1
            external = f"prov-{key[:8]}-1"
            self.events_by_key[key] = external
            raise TimeoutError("response lost after provider commit")
        self.create_calls += 1
        external = f"prov-{key[:8]}-{self.create_calls}"
        self.events_by_key[key] = external
        return {"external_event_id": external, "created": True}

    async def verify(self, result: dict[str, object]) -> bool:
        return bool(result.get("external_event_id"))


async def _drive_scenario(name: str, adapter: _ScenarioAdapter) -> ScenarioResult:
    from personal_pm_worker.calendar.executor import CalendarCommandExecutor
    from personal_pm_worker.calendar.repository import InMemoryOutboxRepository

    repo = InMemoryOutboxRepository()
    executor = CalendarCommandExecutor(repository=repo, adapter=adapter)
    record_id = await repo.add_pending(
        idempotency_key=f"key-{name}", command={"idempotency_key": f"key-{name}"}
    )

    if name == "api-timeout" or name == "provider-success-response-lost":
        # Provider commits but the response is lost; redelivery must reconcile.
        first = await executor.execute(record_id)
        assert first == "PENDING"
        second = await executor.execute(record_id)
        status = await repo.execution_status(record_id)
        ok = second == "SUCCEEDED" and status == "SUCCEEDED"
        return ScenarioResult(
            name, ok, f"reconciled after lost response (calls={adapter.create_calls})"
        )

    if name == "rate-limit-429" or name == "provider-5xx":
        from personal_pm_worker.calendar.retry import classify_failure

        decision = classify_failure(429 if name == "rate-limit-429" else 503, None, 1)
        ok = decision.action == "RETRY" and (decision.delay_seconds or 0) <= 900
        return ScenarioResult(name, ok, f"decision={decision.action}")

    if name == "oauth-expired":
        from personal_pm_worker.calendar.retry import classify_failure

        adapter.reauth_required = True
        decision = classify_failure(401, "invalid_grant", 1)
        ok = decision.action == "NEEDS_REAUTHORIZATION" and decision.delay_seconds is None
        return ScenarioResult(name, ok, "reauthorization required")

    # duplicate-worker-delivery / crash-after-db-commit: double delivery.
    await executor.execute(record_id)
    await executor.execute(record_id)
    status = await repo.execution_status(record_id)
    ext = await repo.external_event_id(record_id)
    ok = adapter.create_calls == 1 and status == "SUCCEEDED" and ext is not None
    return ScenarioResult(
        name, ok, f"duplicate-safe (create_calls={adapter.create_calls}, ext={ext is not None})"
    )


def run_fault_scenarios(
    suite: Sequence[dict[str, object]],
    *,
    required: Sequence[str] = REQUIRED_SCENARIOS,
) -> FaultReport:
    import asyncio

    present = {str(case["scenario"]) for case in suite}
    results: list[ScenarioResult] = []
    for name in required:
        if name not in present:
            results.append(ScenarioResult(name, False, "missing from suite"))
            continue
        adapter = _ScenarioAdapter(scenario=name)
        results.append(asyncio.run(_drive_scenario(name, adapter)))

    duplicate_failures = sum(
        1
        for r in results
        if not r.passed
        and "duplicate" in r.scenario
        or (not r.passed and r.scenario in ("duplicate-worker-delivery", "crash-after-db-commit"))
    )
    false_success_failures = sum(
        1 for r in results if not r.passed and "response-lost" in r.scenario
    )
    reauth_failures = sum(1 for r in results if not r.passed and r.scenario == "oauth-expired")
    metrics = {
        "EXT-002": {"failures": duplicate_failures},
        "EXT-003": {"failures": false_success_failures},
        "EXT-006": {"failures": reauth_failures},
    }
    return FaultReport(results=tuple(results), metrics=metrics, total=len(suite))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Calendar Stage C fault gates")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    suite = [{"scenario": name} for name in REQUIRED_SCENARIOS]
    report = run_fault_scenarios(suite)
    payload = {
        "total": report.total,
        "metrics": report.metrics,
        "results": [
            {"scenario": r.scenario, "passed": r.passed, "detail": r.detail} for r in report.results
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    all_passed = all(r.passed for r in report.results)
    print(f"wrote {args.output}; all_passed={all_passed}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
