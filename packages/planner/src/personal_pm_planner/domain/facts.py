"""Verified facts and their provenance.

Raw source content is untrusted and lives outside Planning Core; a SourceFact
records only the verified statement plus where it came from.
"""

from dataclasses import dataclass
from datetime import datetime

from personal_pm_planner.domain.time import require_aware_utc


@dataclass(frozen=True, slots=True)
class SourceReference:
    """Points at the origin of a fact without embedding untrusted content."""

    artifact_kind: str
    artifact_id: str
    location: str

    def __post_init__(self) -> None:
        if not self.artifact_kind.strip() or not self.artifact_id.strip():
            raise ValueError("source reference requires artifact kind and id")


@dataclass(frozen=True, slots=True)
class SourceFact:
    subject: str
    value: str
    source: SourceReference
    recorded_at: datetime

    def __post_init__(self) -> None:
        require_aware_utc(self.recorded_at)
