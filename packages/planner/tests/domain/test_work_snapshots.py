from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from uuid import UUID

import pytest
from personal_pm_planner.domain.enums import (
    DeadlineType,
    ImportanceLevel,
    WorkstreamStatus,
)
from personal_pm_planner.domain.facts import SourceFact, SourceReference
from personal_pm_planner.domain.identifiers import (
    AreaId,
    MilestoneId,
    WorkspaceId,
    WorkstreamId,
)
from personal_pm_planner.domain.work import (
    AreaSnapshot,
    MilestoneSnapshot,
    WorkstreamSnapshot,
)

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))


@pytest.fixture
def milestone_factory():
    def factory(**overrides: object) -> MilestoneSnapshot:
        defaults: dict[str, object] = {
            "id": MilestoneId(UUID("00000000-0000-0000-0000-000000000002")),
            "workspace_id": WORKSPACE,
            "workstream_id": WorkstreamId(UUID("00000000-0000-0000-0000-000000000003")),
            "title": "데이터베이스 과제 2 제출",
            "deadline_date": date(2026, 9, 10),
            "deadline_at": None,
            "deadline_date_known": True,
            "deadline_time_known": False,
            "deadline_type": DeadlineType.HARD_DEADLINE,
            "required_buffer_minutes": 60,
            "version": 1,
        }
        defaults.update(overrides)
        if isinstance(defaults["deadline_date"], str):
            defaults["deadline_date"] = date.fromisoformat(str(defaults["deadline_date"]))
        return MilestoneSnapshot(**defaults)  # type: ignore[arg-type]

    return factory


def test_date_only_deadline_does_not_fabricate_time(milestone_factory) -> None:
    milestone: MilestoneSnapshot = milestone_factory(
        deadline_date="2026-09-10", deadline_at=None
    )
    assert milestone.deadline_date == date(2026, 9, 10)
    assert milestone.deadline_date_known is True
    assert milestone.deadline_time_known is False
    assert milestone.deadline_at is None


def test_known_time_requires_a_fact_instant(milestone_factory) -> None:
    with pytest.raises(ValueError, match="known deadline time requires"):
        milestone_factory(deadline_time_known=True, deadline_at=None)


def test_unknown_time_cannot_persist_a_fact_instant(milestone_factory) -> None:
    with pytest.raises(ValueError, match="unknown deadline time"):
        milestone_factory(
            deadline_time_known=False,
            deadline_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
        )


def test_deadline_instant_must_be_aware(milestone_factory) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        milestone_factory(deadline_time_known=True, deadline_at=datetime(2026, 9, 10, 23, 59))


def test_snapshots_are_immutable(milestone_factory) -> None:
    milestone = milestone_factory()
    with pytest.raises(FrozenInstanceError):
        milestone.title = "변경"  # type: ignore[misc]


def test_area_and_workstream_snapshots_hold_workspace_scope() -> None:
    area = AreaSnapshot(
        id=AreaId(UUID("00000000-0000-0000-0000-000000000004")),
        workspace_id=WORKSPACE,
        name="학교",
        version=1,
    )
    workstream = WorkstreamSnapshot(
        id=WorkstreamId(UUID("00000000-0000-0000-0000-000000000003")),
        workspace_id=WORKSPACE,
        area_id=area.id,
        name="데이터베이스 수업",
        importance=ImportanceLevel.PROTECTED,
        status=WorkstreamStatus.ACTIVE,
        version=1,
    )
    assert area.workspace_id == workstream.workspace_id == WORKSPACE


def test_importance_levels_are_canonical() -> None:
    assert {level.value for level in ImportanceLevel} == {
        "protected",
        "important",
        "normal",
        "optional",
        "on_hold",
    }


def test_source_fact_keeps_provenance() -> None:
    reference = SourceReference(
        artifact_kind="document",
        artifact_id="syllabus-db-2026",
        location="page 2 paragraph 4",
    )
    fact = SourceFact(
        subject="milestone:db-assignment-2",
        value="due 2026-09-10",
        source=reference,
        recorded_at=datetime(2026, 8, 23, 3, 2, 15, tzinfo=UTC),
    )
    assert fact.source.location == "page 2 paragraph 4"
