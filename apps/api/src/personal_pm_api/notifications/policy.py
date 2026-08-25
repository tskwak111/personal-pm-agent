"""Notification intents and deterministic delivery policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class NotificationSeverity(Enum):
    CRITICAL = "CRITICAL"
    ACTIONABLE = "ACTIONABLE"
    SUMMARY = "SUMMARY"
    SILENT = "SILENT"


class DeliveryMode(Enum):
    IMMEDIATE = "IMMEDIATE"
    NEXT_SUMMARY = "NEXT_SUMMARY"
    RECORD_ONLY = "RECORD_ONLY"


@dataclass(frozen=True, slots=True)
class NotificationIntent:
    dedupe_key: str
    severity: NotificationSeverity
    title: str
    body: str


def delivery_mode(
    intent: NotificationIntent,
    settings: Any,
    now: datetime,
) -> DeliveryMode:
    """Critical bypasses quiet hours; silent is record-only; summary defers."""
    if intent.severity is NotificationSeverity.SILENT:
        return DeliveryMode.RECORD_ONLY
    if settings.is_quiet(now) and intent.severity is not NotificationSeverity.CRITICAL:
        return DeliveryMode.NEXT_SUMMARY
    if intent.severity is NotificationSeverity.SUMMARY:
        return DeliveryMode.NEXT_SUMMARY
    return DeliveryMode.IMMEDIATE


__all__ = [
    "DeliveryMode",
    "NotificationIntent",
    "NotificationSeverity",
    "delivery_mode",
]
