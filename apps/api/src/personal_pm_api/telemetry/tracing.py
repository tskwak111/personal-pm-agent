"""Lightweight trace context propagation (W3C-style ids)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


def _new_id() -> str:
    return secrets.token_hex(16)


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str

    @classmethod
    def new(cls) -> TraceContext:
        return cls(trace_id=_new_id(), span_id=_new_id())

    def child_span(self, name: str) -> TraceContext:  # noqa: ARG004 — name kept for callers
        return TraceContext(trace_id=self.trace_id, span_id=_new_id())


__all__ = ["TraceContext"]
