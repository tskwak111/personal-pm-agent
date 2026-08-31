#!/usr/bin/env python3
"""Run every Stage A hard gate from explicit test observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_MAP = ROOT / "evals/planner-vectors/gate-test-map.json"
GENERATED_RUNNER = ROOT / "packages/planner/tests/properties/test_generated_scenarios.py"
GENERATED_NODE = (
    "packages/planner/tests/properties/test_generated_scenarios.py::"
    "test_generated_plans_obey_capacity_and_determinism"
)

HARD_GATES = (
    "SAFE-001",
    "SAFE-002",
    "SAFE-003",
    "SAFE-004",
    "SAFE-005",
    "SAFE-006",
    "PLAN-001",
    "PLAN-002",
    "PLAN-003",
    "PLAN-004",
    "PLAN-005",
    "PLAN-006",
    "PLAN-007",
    "PLAN-008",
    "PLAN-009",
)


@dataclass(frozen=True, slots=True)
class GateObservation:
    executed: bool
    checks: int
    failures: int
    source: str


@dataclass(frozen=True, slots=True)
class GateResult:
    gate: str
    executed: bool
    checks: int
    failures: int
    source: str
    passed: bool


@dataclass(frozen=True, slots=True)
class EnvironmentSnapshot:
    python_version: str
    cpu_model: str
    memory_bytes: int


@dataclass(frozen=True, slots=True)
class StageAReport:
    overall: str
    scenarios: int
    gates: dict[str, GateResult]
    environment: EnvironmentSnapshot
    code_version: str
    input_hash: str
    generated_at_utc: str


class TestResultsSource(Protocol):
    def observation_for(self, gate: str) -> GateObservation | None: ...


def _sys_memory() -> Any:
    try:
        import os

        pages = getattr(os, "sysconf", None)
        if pages is not None:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        pass
    return 1


def reference_environment() -> EnvironmentSnapshot:
    memory = _sys_memory()
    total = getattr(memory, "total", memory)
    try:
        memory_bytes = int(total)
    except (TypeError, ValueError):
        memory_bytes = 1
    return EnvironmentSnapshot(
        python_version=platform.python_version(),
        cpu_model=platform.processor() or platform.machine(),
        memory_bytes=max(1, memory_bytes),
    )


def overall_stage_a(gates: dict[str, GateResult]) -> str:
    return "PASS" if all(gates[gate].passed for gate in HARD_GATES) else "FAIL"


def build_stage_a_report(
    test_results: TestResultsSource,
    *,
    scenarios: int,
    code_version: str = "dev",
    input_hash: str = "unknown",
    generated_at_utc: str = "unknown",
) -> StageAReport:
    gates: dict[str, GateResult] = {}
    for gate in HARD_GATES:
        observation = test_results.observation_for(gate)
        if observation is None:
            observation = GateObservation(False, 0, 0, "MISSING")
        gates[gate] = GateResult(
            gate=gate,
            executed=observation.executed,
            checks=observation.checks,
            failures=observation.failures,
            source=observation.source,
            passed=observation.executed and observation.checks > 0 and observation.failures == 0,
        )
    return StageAReport(
        overall=overall_stage_a(gates),
        scenarios=scenarios,
        gates=gates,
        environment=reference_environment(),
        code_version=code_version,
        input_hash=input_hash,
        generated_at_utc=generated_at_utc,
    )


def property_command(scenarios: int, observations: Path) -> list[str]:
    return [
        sys.executable,
        str(GENERATED_RUNNER),
        "--scenarios",
        str(scenarios),
        "--observations",
        str(observations),
    ]


def _load_gate_map(path: Path) -> dict[str, list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != set(HARD_GATES):
        raise ValueError("gate map must contain every Stage A hard gate exactly once")
    result: dict[str, list[str]] = {}
    for gate, nodes in raw.items():
        if (
            not isinstance(nodes, list)
            or not nodes
            or not all(isinstance(node, str) for node in nodes)
        ):
            raise ValueError(f"gate map entry must contain pytest nodes: {gate}")
        result[str(gate)] = nodes
    return result


def _run_pytest(nodes: list[str]) -> GateObservation:
    result = subprocess.run(  # noqa: S603 - version-controlled pytest nodes
        [sys.executable, "-m", "pytest", *nodes, "-m", "integration or not integration", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    detail = (result.stdout + result.stderr).strip()[-4000:]
    return GateObservation(
        executed=True,
        checks=len(nodes),
        failures=0 if result.returncode == 0 else 1,
        source=";".join(nodes) + (f" | {detail}" if result.returncode else ""),
    )


def _load_generated(path: Path, scenarios: int) -> dict[str, GateObservation]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("scenario_count") != scenarios or not isinstance(raw.get("gates"), dict):
        return {}
    result: dict[str, GateObservation] = {}
    for gate, item in raw["gates"].items():
        if gate not in HARD_GATES or not isinstance(item, dict):
            continue
        result[gate] = GateObservation(
            executed=item.get("executed") is True,
            checks=int(item.get("checks", 0)),
            failures=int(item.get("failures", 0)),
            source=str(item.get("source", "generated scenarios")),
        )
    return result


class DictResults:
    def __init__(self, values: dict[str, GateObservation]) -> None:
        self.values = values

    def observation_for(self, gate: str) -> GateObservation | None:
        return self.values.get(gate)


def _revision() -> str:
    result = subprocess.run(  # noqa: S603 - fixed git command
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage A evaluation")
    parser.add_argument("--scenarios", type=int, default=20000)
    parser.add_argument("--gate-map", type=Path, default=DEFAULT_GATE_MAP)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.scenarios < 1:
        parser.error("--scenarios must be positive")

    gate_map = _load_gate_map(args.gate_map)
    observations: dict[str, GateObservation] = {}
    with tempfile.TemporaryDirectory(prefix="pma-stage-a-") as temporary:
        generated_path = Path(temporary) / "generated-observations.json"
        generated_result = subprocess.run(  # noqa: S603 - fixed runner command
            property_command(args.scenarios, generated_path),
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        generated = _load_generated(generated_path, args.scenarios)
        if generated_result.returncode != 0 and not generated:
            generated = {
                gate: GateObservation(True, 0, 1, GENERATED_NODE)
                for gate in ("PLAN-001", "PLAN-004", "PLAN-006")
            }

        for gate, nodes in gate_map.items():
            if nodes == [GENERATED_NODE]:
                if gate in generated:
                    observations[gate] = generated[gate]
                continue
            observation = _run_pytest(nodes)
            generated_observation = generated.get(gate)
            if generated_observation is not None:
                observation = GateObservation(
                    executed=observation.executed and generated_observation.executed,
                    checks=observation.checks + generated_observation.checks,
                    failures=observation.failures + generated_observation.failures,
                    source=f"{observation.source};{generated_observation.source}",
                )
            observations[gate] = observation

    input_hash = hashlib.sha256(
        args.gate_map.read_bytes() + b"\0" + str(args.scenarios).encode("ascii")
    ).hexdigest()
    report = build_stage_a_report(
        DictResults(observations),
        scenarios=args.scenarios,
        code_version=_revision(),
        input_hash=input_hash,
        generated_at_utc=datetime.now(UTC).isoformat(),
    )
    payload = {
        "schema_version": "1.0",
        "overall": report.overall,
        "scenarios": report.scenarios,
        "code_version": report.code_version,
        "input_hash": report.input_hash,
        "generated_at_utc": report.generated_at_utc,
        "environment": {
            "python_version": report.environment.python_version,
            "cpu_model": report.environment.cpu_model,
            "memory_bytes": report.environment.memory_bytes,
        },
        "gates": {
            gate: {
                "executed": result.executed,
                "checks": result.checks,
                "failures": result.failures,
                "source": result.source,
                "passed": result.passed,
            }
            for gate, result in report.gates.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}; overall={report.overall}")
    return 0 if report.overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
