from datetime import UTC, datetime, timedelta
from uuid import UUID

from personal_pm_planner.contracts.input import PlannerInput
from personal_pm_planner.domain.availability import ExternalDependencySnapshot
from personal_pm_planner.domain.dependency import TaskDependency
from personal_pm_planner.domain.enums import DeadlineType, DependencyType
from personal_pm_planner.domain.identifiers import ExternalDependencyId, TaskId

from tests.conftest import make_task

DEADLINE_UTC = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)


def build_case(
    *,
    tasks,
    dependencies,
    externals=(),
    buffer_minutes=60,
):
    from personal_pm_planner.domain.work import MilestoneSnapshot

    first = tasks[0]
    milestone = MilestoneSnapshot(
        id=first.milestone_id,
        workspace_id=first.workspace_id,
        workstream_id=first.workstream_id,
        title="제출",
        deadline_date=None,
        deadline_at=DEADLINE_UTC,
        deadline_date_known=False,
        deadline_time_known=True,
        deadline_type=DeadlineType.HARD_DEADLINE,
        required_buffer_minutes=buffer_minutes,
        version=1,
    )
    return PlannerInput(
        planner_version="planner-spec-1.0",
        now_utc=datetime(2026, 9, 9, 9, 0, tzinfo=UTC),
        user_timezone="Asia/Seoul",
        horizon_end_utc=DEADLINE_UTC + timedelta(days=1),
        slot_minutes=15,
        availability_windows=(),
        calendar_events=(),
        tasks=tuple(tasks),
        milestones=(milestone,),
        task_dependencies=tuple(dependencies),
        external_dependencies=tuple(externals),
        pinned_task_ids=frozenset(),
        excluded_dates=(),
    )


def make_external(task_id: TaskId, workspace_id) -> ExternalDependencySnapshot:
    return ExternalDependencySnapshot(
        id=ExternalDependencyId(UUID(int=300)),
        workspace_id=workspace_id,
        deliverable="데이터셋",
        owner_label="민수",
        expected_delivery_at=DEADLINE_UTC - timedelta(hours=24),
        uncertainty_buffer_minutes=60,
        fallback_available=False,
        fallback_task_ids=(),
        affected_task_ids=(task_id,),
        version=1,
    )


def test_cycle_tasks_are_blocked_but_remain_in_demand() -> None:
    from personal_pm_planner.graph.build import build_graph_analysis

    a, b, c = TaskId(UUID(int=1)), TaskId(UUID(int=2)), TaskId(UUID(int=3))
    value = build_case(
        tasks=[make_task(1), make_task(2), make_task(3)],
        dependencies=[
            TaskDependency(a, b, DependencyType.BLOCKS_START),
            TaskDependency(b, c, DependencyType.BLOCKS_START),
            TaskDependency(c, a, DependencyType.BLOCKS_START),
        ],
    )
    result = build_graph_analysis(value)
    assert set(result.blocked_task_ids) == {a, b, c}
    assert result.cycles[0].rule_id == "DEPENDENCY_CYCLE"
    assert set(result.cycles[0].task_ids) == {a, b, c}
    assert result.required_demand_minutes > 0


def test_external_handoff_is_computed_backwards() -> None:
    from personal_pm_planner.graph.build import build_graph_analysis

    t1, t2 = TaskId(UUID(int=1)), TaskId(UUID(int=2))
    tasks = [
        make_task(1, base=90, safety=120, deadline_date=None),
        make_task(2, base=45, safety=60, deadline_date=None),
    ]
    value = build_case(
        tasks=tasks,
        dependencies=[TaskDependency(t1, t2, DependencyType.BLOCKS_START)],
        externals=(make_external(t1, tasks[0].workspace_id),),
    )
    result = build_graph_analysis(value)
    # latest_finish(T2)=D-60buffer -> latest_start(T2)=D-120
    # latest_finish(T1)=min(D-60, D-120)=D-120 -> latest_start(T1)=D-240
    assert result.external_dependencies[0].latest_safe_handoff_at == DEADLINE_UTC - timedelta(
        minutes=240
    )
    assert result.must_start_by_at[t2] == DEADLINE_UTC - timedelta(minutes=120)
    assert result.must_start_by_at[t1] == DEADLINE_UTC - timedelta(minutes=240)


def test_unlock_counts_follow_blocks_start_edges() -> None:
    from personal_pm_planner.graph.build import build_graph_analysis

    a, b = TaskId(UUID(int=1)), TaskId(UUID(int=2))
    value = build_case(
        tasks=[make_task(1), make_task(2)],
        dependencies=[TaskDependency(a, b, DependencyType.BLOCKS_START)],
    )
    result = build_graph_analysis(value)
    assert result.critical_path_unlock_count[a] == 1
    assert result.critical_path_unlock_count[b] == 0


def test_done_predecessor_keeps_successor_schedulable() -> None:
    from personal_pm_planner.domain.enums import TaskStatus
    from personal_pm_planner.graph.build import build_graph_analysis

    a, b = TaskId(UUID(int=1)), TaskId(UUID(int=2))
    done_pred = make_task(1)
    object.__setattr__(done_pred, "status", TaskStatus.DONE)
    object.__setattr__(done_pred, "remaining_base_minutes", 0)
    object.__setattr__(done_pred, "remaining_safety_minutes", 0)
    value = build_case(
        tasks=[done_pred, make_task(2)],
        dependencies=[TaskDependency(a, b, DependencyType.BLOCKS_START)],
    )
    result = build_graph_analysis(value)
    assert b not in result.blocked_task_ids
    assert result.ready_to_schedule(b) is True
