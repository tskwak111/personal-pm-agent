"""Lightweight trace context propagation (W3C-style ids)."""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

_CORRELATION_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}").fullmatch


def _new_id() -> str:
    return secrets.token_hex(16)


def resolve_correlation_id(value: str | None) -> str:
    """Accept a log-safe caller ID or generate an opaque replacement."""
    return value if value is not None and _CORRELATION_ID(value) else _new_id()


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: str
    span_id: str

    @classmethod
    def new(cls) -> TraceContext:
        return cls(trace_id=_new_id(), span_id=_new_id())

    def child_span(self, name: str) -> TraceContext:  # noqa: ARG004 — name kept for callers
        return TraceContext(trace_id=self.trace_id, span_id=_new_id())


__all__ = ["TraceContext", "resolve_correlation_id"]
