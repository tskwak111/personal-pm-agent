"""Request/response schemas for workspace planning commands."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class TaskTransitionRequest(BaseModel):
    expected_version: int
    target_status: str
    completion_confirmed: bool = False
    waiting_resolved: bool = False
    blocker_resolved: bool = False
    waiting_reason: str | None = None

    @field_validator("target_status")
    @classmethod
    def lowercase_status(cls, value: str) -> str:
        return value.lower()


class MilestoneDeadlinePatchRequest(BaseModel):
    expected_version: int
    deadline_date: str | None = None  # ISO date; time changes stay explicit elsewhere
