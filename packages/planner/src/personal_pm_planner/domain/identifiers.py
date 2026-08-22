"""Canonical typed identifiers scoped to a workspace."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, order=True)
class WorkspaceId:
    value: UUID
