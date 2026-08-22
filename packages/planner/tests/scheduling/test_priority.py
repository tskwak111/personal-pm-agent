from datetime import UTC, datetime
from uuid import UUID

import pytest
from personal_pm_planner.domain.enums import DeadlineType, ImportanceLevel


def make_schedulable(**overrides):
    from personal_pm_planner.domain.identifiers import TaskId
    from personal_pm_planner.scheduling.priority import PriorityClass, SchedulableTask

    defaults = {
        "id": TaskId(UUID(int=10)),
        "priority_class": PriorityClass.P2,
        "must_start_by_at": None,
        "effective_deadline_at": None,
        "critical_path_unlock_count": 0,
        "external_commitment": False,
        "user_importance": ImportanceLevel.NORMAL,
        "prior_plan_position": None,
        "context_switch_penalty": 1,
        "created_at": datetime(2026, 8, 20, tzinfo=UTC),
        "llm_score": None,
    }
    defaults.update(overrides)
    return SchedulableTask(**defaults)


@pytest.fixture
def priority_context():
    from personal_pm_planner.scheduling.priority import PriorityContext

    return PriorityContext(now_utc=datetime(2026, 8, 23, tzinfo=UTC))


@pytest.fixture
def tied_tasks():
    # Identical business attributes; only UUIDs differ.
    return [make_schedulable(id=UUID(int=value)) for value in (30, 10, 20)]


def test_identical_business_priority_uses_task_id_as_final_tie_break(
    priority_context, tied_tasks
) -> None:
    from personal_pm_planner.scheduling.priority import priority_key

    ordered = sorted(tied_tasks, key=lambda task: priority_key(task, priority_context))
    assert [task.id.value.hex for task in ordered] == sorted(
        task.id.value.hex for task in tied_tasks
    )


def test_llm_score_is_not_part_of_key(priority_context) -> None:
    from personal_pm_planner.scheduling.priority import priority_key

    base = make_schedulable()
    low = make_schedulable(llm_score=0.01)
    high = make_schedulable(llm_score=0.99)
    assert (
        priority_key(low, priority_context)
        == priority_key(base, priority_context)
        == priority_key(high, priority_context)
    )


def test_priority_class_precedes_everything(priority_context) -> None:
    import personal_pm_planner.scheduling.priority as sp

    rescue = make_schedulable(
        priority_class=sp.PriorityClass.P0,
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )
    protect_late = make_schedulable(
        priority_class=sp.PriorityClass.P1,
        effective_deadline_at=datetime(2026, 8, 24, tzinfo=UTC),
    )
    ordered = sorted([protect_late, rescue], key=lambda t: sp.priority_key(t, priority_context))
    assert ordered[0].priority_class is sp.PriorityClass.P0


def test_must_start_by_beats_unlock_count(priority_context) -> None:
    from personal_pm_planner.scheduling.priority import priority_key

    early = make_schedulable(must_start_by_at=datetime(2026, 8, 25, tzinfo=UTC))
    many_unlocks = make_schedulable(critical_path_unlock_count=9)
    ordered = sorted([many_unlocks, early], key=lambda t: priority_key(t, priority_context))
    assert ordered[0] is early


def test_external_commitment_and_prior_position_ordering(priority_context) -> None:
    from personal_pm_planner.scheduling.priority import priority_key

    committed = make_schedulable(external_commitment=True, prior_plan_position=5)
    positioned = make_schedulable(prior_plan_position=1)
    ordered = sorted([committed, positioned], key=lambda t: priority_key(t, priority_context))
    assert ordered[0] is positioned


def test_initial_classification_rules() -> None:
    from personal_pm_planner.scheduling.priority import initial_priority_class

    assert initial_priority_class(
        verified_deadline_passed=True,
        deadline_type=DeadlineType.HARD_DEADLINE,
        importance=ImportanceLevel.PROTECTED,
    ).name.startswith("P0")
    assert (
        initial_priority_class(
            verified_deadline_passed=False,
            deadline_type=DeadlineType.HARD_DEADLINE,
            importance=ImportanceLevel.PROTECTED,
        ).value
        == "P1"
    )
    assert (
        initial_priority_class(
            verified_deadline_passed=False,
            deadline_type=DeadlineType.SOFT_GOAL,
            importance=ImportanceLevel.IMPORTANT,
            is_synthetic_buffer=True,
        ).value
        == "P1"
    )
    assert (
        initial_priority_class(
            verified_deadline_passed=False,
            deadline_type=DeadlineType.SOFT_GOAL,
            importance=ImportanceLevel.OPTIONAL,
            is_exploration=True,
        ).value
        == "P4"
    )
    assert (
        initial_priority_class(
            verified_deadline_passed=False,
            deadline_type=DeadlineType.SOFT_GOAL,
            importance=ImportanceLevel.NORMAL,
            is_routine=True,
        ).value
        == "P3"
    )
