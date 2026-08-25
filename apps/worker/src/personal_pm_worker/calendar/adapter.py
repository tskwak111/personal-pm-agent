"""Provider event value type used by the calendar adapter port."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProviderEvent:
    external_id: str
    title: str
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    blocks_time: bool = True
    status: str = "confirmed"
    managed_focus_block: bool = False
    transparency: str = "opaque"
    provider_version: int | None = None


__all__ = ["ProviderEvent"]
