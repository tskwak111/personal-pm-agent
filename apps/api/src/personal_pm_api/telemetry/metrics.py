"""Small Prometheus registry with fixed metric and label contracts."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)

COUNTER_LABELS: dict[str, tuple[str, ...]] = {
    "http_requests_total": ("method", "route", "status"),
    "planner_runs_total": ("result",),
    "plan_snapshots_appended_total": (),
    "outbox_jobs_total": ("result",),
    "external_executions_failed_total": (),
    "external_execution_verifications_total": ("result",),
    "oauth_exchange_failures_total": (),
}
HISTOGRAM_LABELS: dict[str, tuple[str, ...]] = {
    "http_request_duration_seconds": ("method", "route", "status"),
    "planner_latency_seconds": ("result",),
}
METRIC_LABELS = {**COUNTER_LABELS, **HISTOGRAM_LABELS}
REGISTERED_METRICS = frozenset(METRIC_LABELS)


@dataclass(slots=True)
class _Histogram:
    buckets: list[int]
    count: int = 0
    total: float = 0.0


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[str, ...]], int] = {}
        self._histograms: dict[tuple[str, tuple[str, ...]], _Histogram] = {}

    @staticmethod
    def _values(name: str, labels: dict[str, str]) -> tuple[str, ...]:
        expected = METRIC_LABELS.get(name)
        if expected is None:
            raise ValueError(f"unknown metric {name}")
        if set(labels) != set(expected):
            raise ValueError(f"labels for {name} must be {expected}")
        return tuple(str(labels[key]) for key in expected)

    def increment(self, name: str, amount: int = 1, **labels: str) -> None:
        if name not in COUNTER_LABELS or amount < 0:
            raise ValueError(f"invalid counter update for {name}")
        key = (name, self._values(name, labels))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        if name not in HISTOGRAM_LABELS or value < 0:
            raise ValueError(f"invalid histogram observation for {name}")
        key = (name, self._values(name, labels))
        with self._lock:
            state = self._histograms.setdefault(
                key, _Histogram(buckets=[0] * len(HISTOGRAM_BUCKETS))
            )
            state.count += 1
            state.total += value
            for index, boundary in enumerate(HISTOGRAM_BUCKETS):
                if value <= boundary:
                    state.buckets[index] += 1

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, values), count in sorted(self._counters.items()):
                lines.append(f"{name}{_labels(name, values)} {count}")
            for (name, values), state in sorted(self._histograms.items()):
                for boundary, count in zip(HISTOGRAM_BUCKETS, state.buckets, strict=True):
                    lines.append(
                        f"{name}_bucket{_labels(name, values, le=format(boundary, 'g'))} {count}"
                    )
                lines.append(f"{name}_bucket{_labels(name, values, le='+Inf')} {state.count}")
                lines.append(f"{name}_sum{_labels(name, values)} {format(state.total, 'g')}")
                lines.append(f"{name}_count{_labels(name, values)} {state.count}")
        return "\n".join(lines) + "\n"


def _labels(name: str, values: tuple[str, ...], *, le: str | None = None) -> str:
    pairs = list(zip(METRIC_LABELS[name], values, strict=True))
    if le is not None:
        pairs.append(("le", le))
    if not pairs:
        return ""
    rendered = ",".join(f'{key}="{_escape(value)}"' for key, value in pairs)
    return "{" + rendered + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


RUNTIME_METRICS = MetricsRegistry()

__all__ = [
    "METRIC_LABELS",
    "REGISTERED_METRICS",
    "MetricsRegistry",
    "RUNTIME_METRICS",
]
