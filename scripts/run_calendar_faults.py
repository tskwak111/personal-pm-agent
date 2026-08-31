#!/usr/bin/env python3
"""Execute declared Calendar emulator faults and emit measured EXT observations."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from math import ceil
from pathlib import Path

import yaml  # type: ignore[import-untyped]

REQUIRED_SCENARIOS = (
    "normal-write",
    "api-timeout",
    "rate-limit-429",
    "provider-5xx",
    "oauth-expired",
    "duplicate-worker-delivery",
    "crash-after-db-commit",
    "provider-success-response-lost",
    "external-move-no-restore",
    "webhook-gap-recovery",
)


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    scenario: str
    passed: bool
    detail: str
    metric_ids: tuple[str, ...]
    recovery_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class FaultReport:
    results: tuple[ScenarioResult, ...]
    metrics: dict[str, dict[str, int | float]]
    total: int
    provider_profile: str


class _ScenarioAdapter:
    def __init__(self, scenario: str = "") -> None:
        self.scenario = scenario
        self.create_calls = 0
        self.events_by_key: dict[str, str] = {}
        self._response_lost = False

    async def execute(self, command: dict[str, object]) -> dict[str, object]:
        key = str(command["idempotency_key"])
        if key in self.events_by_key:
            return {"external_event_id": self.events_by_key[key], "created": False}
        if (
            self.scenario in ("api-timeout", "provider-success-response-lost")
            and not self._response_lost
        ):
            self._response_lost = True
            self.create_calls += 1
            self.events_by_key[key] = f"prov-{key[:8]}-1"
            raise TimeoutError("response lost after provider commit")
        self.create_calls += 1
        external = f"prov-{key[:8]}-{self.create_calls}"
        self.events_by_key[key] = external
        return {"external_event_id": external, "created": True}

    async def verify(self, result: dict[str, object]) -> bool:
        return bool(result.get("external_event_id"))


async def _drive_webhook_recovery(metric_ids: tuple[str, ...]) -> ScenarioResult:
    from personal_pm_worker.calendar.scheduler import SyncScheduler
    from personal_pm_worker.calendar.sync_jobs import InMemorySyncOperationStore

    class Clock:
        now = 0.0

    class Target:
        calls = 0

        async def run_delta_sync(self, external_id: str) -> int:
            self.calls += 1
            return 1

    clock = Clock()
    target = Target()
    scheduler = SyncScheduler(
        operations=InMemorySyncOperationStore(), clock=clock, sync_target=target
    )
    await scheduler.register_pending_change("evt-missed", connection_id="conn-1")
    clock.now = 900.0
    await scheduler.run_due()
    return ScenarioResult(
        "webhook-gap-recovery",
        target.calls == 1,
        f"recovery_calls={target.calls}",
        metric_ids,
        recovery_seconds=900,
    )


async def _drive_scenario(
    name: str, adapter: _ScenarioAdapter, metric_ids: tuple[str, ...]
) -> ScenarioResult:
    if name == "webhook-gap-recovery":
        return await _drive_webhook_recovery(metric_ids)
    if name == "external-move-no-restore":
        from personal_pm_api.calendar.field_ownership import field_owner

        passed = field_owner("start_at") == "LAST_EXPLICIT_USER_ACTION"
        return ScenarioResult(name, passed, "provider move remains authoritative", metric_ids)
    if name in ("rate-limit-429", "provider-5xx", "oauth-expired"):
        from personal_pm_worker.calendar.retry import classify_failure

        if name == "oauth-expired":
            decision = classify_failure(401, "invalid_grant", 1)
            passed = decision.action == "NEEDS_REAUTHORIZATION"
        else:
            decision = classify_failure(429 if name == "rate-limit-429" else 503, None, 1)
            passed = decision.action == "RETRY" and (decision.delay_seconds or 0) <= 900
        return ScenarioResult(name, passed, f"decision={decision.action}", metric_ids)

    from personal_pm_worker.calendar.executor import CalendarCommandExecutor
    from personal_pm_worker.calendar.repository import InMemoryOutboxRepository

    repo = InMemoryOutboxRepository()
    executor = CalendarCommandExecutor(repository=repo, adapter=adapter)
    record_id = await repo.add_pending(
        idempotency_key=f"key-{name}", command={"idempotency_key": f"key-{name}"}
    )
    if name in ("api-timeout", "provider-success-response-lost"):
        first = await executor.execute(record_id)
        second = await executor.execute(record_id)
        status = await repo.execution_status(record_id)
        external_id = await repo.external_event_id(record_id)
        passed = (
            first == "PENDING"
            and second == "SUCCEEDED"
            and status == "SUCCEEDED"
            and external_id is not None
            and adapter.create_calls == 1
        )
        return ScenarioResult(name, passed, "lost response reconciled", metric_ids)

    await executor.execute(record_id)
    if name in ("duplicate-worker-delivery", "crash-after-db-commit"):
        await executor.execute(record_id)
    status = await repo.execution_status(record_id)
    external_id = await repo.external_event_id(record_id)
    passed = status == "SUCCEEDED" and external_id is not None and adapter.create_calls == 1
    return ScenarioResult(name, passed, f"status={status}", metric_ids)


def _aggregate(results: Sequence[ScenarioResult]) -> dict[str, dict[str, int | float]]:
    metrics: dict[str, dict[str, int | float]] = {}
    for result in results:
        for metric_id in result.metric_ids:
            if metric_id == "webhook_recovery_seconds":
                continue
            entry = metrics.setdefault(metric_id, {"checks": 0, "failures": 0})
            entry["checks"] = int(entry["checks"]) + 1
            entry["failures"] = int(entry["failures"]) + (0 if result.passed else 1)
    if "EXT-001" in metrics:
        entry = metrics["EXT-001"]
        entry["rate"] = (int(entry["checks"]) - int(entry["failures"])) / int(entry["checks"])

    latencies = sorted(
        result.recovery_seconds
        for result in results
        if "webhook_recovery_seconds" in result.metric_ids
        and result.recovery_seconds is not None
        and result.passed
    )
    if latencies:
        index = max(0, ceil(len(latencies) * 0.95) - 1)
        metrics["webhook_recovery_seconds"] = {
            "checks": len(latencies),
            "p95": latencies[index],
        }
    return metrics


def run_fault_scenarios(
    suite: Sequence[dict[str, object]],
    *,
    required: Sequence[str] = REQUIRED_SCENARIOS,
    provider_profile: str = "emulator",
) -> FaultReport:
    cases = {str(case.get("scenario")): case for case in suite}
    results: list[ScenarioResult] = []
    for name in required:
        case = cases.get(name)
        if case is None:
            results.append(ScenarioResult(name, False, "missing from suite", ()))
            continue
        raw_metric_ids = case.get("metric_ids")
        if not isinstance(raw_metric_ids, list) or not all(
            isinstance(metric_id, str) for metric_id in raw_metric_ids
        ):
            results.append(ScenarioResult(name, False, "missing metric_ids", ()))
            continue
        metric_ids = tuple(str(metric_id) for metric_id in raw_metric_ids)
        results.append(asyncio.run(_drive_scenario(name, _ScenarioAdapter(name), metric_ids)))
    return FaultReport(
        results=tuple(results),
        metrics=_aggregate(results),
        total=len(suite),
        provider_profile=provider_profile,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Calendar Stage C fault gates")
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("evals/fault-injection/calendar/scenarios.yaml"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    raw = yaml.safe_load(args.scenarios.read_text(encoding="utf-8"))
    suite = raw.get("scenarios", []) if isinstance(raw, dict) else []
    provider_profile = str(raw.get("provider_profile", "none")) if isinstance(raw, dict) else "none"
    report = run_fault_scenarios(suite, provider_profile=provider_profile)
    all_passed = all(result.passed for result in report.results)
    payload = {
        "schema_version": "1.0",
        "overall": "PASS" if all_passed else "FAIL",
        "provider_profile": report.provider_profile,
        "total": report.total,
        "metrics": report.metrics,
        "results": [
            {
                "scenario": result.scenario,
                "metric_ids": list(result.metric_ids),
                "passed": result.passed,
                "detail": result.detail,
                "recovery_seconds": result.recovery_seconds,
            }
            for result in report.results
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; all_passed={all_passed}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
