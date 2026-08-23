"""Planning service DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanSnapshotDTO:
    id: str
    status: str
    planner_version: str
    input_hash: str
    is_current: bool
