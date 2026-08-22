from uuid import UUID

import pytest
from personal_pm_planner.domain.dependency import DependencyGraph, TaskDependency
from personal_pm_planner.domain.enums import DependencyType
from personal_pm_planner.domain.errors import DependencyCycleError
from personal_pm_planner.domain.identifiers import TaskId


@pytest.fixture
def task_ids():
    def factory(count: int) -> list[TaskId]:
        return [TaskId(UUID(int=index + 1)) for index in range(count)]

    return factory


def test_cycle_path_is_stable(task_ids) -> None:
    a, b, c = task_ids(3)
    graph = DependencyGraph.from_dependencies(
        [
            TaskDependency(a, b, DependencyType.BLOCKS_START),
            TaskDependency(b, c, DependencyType.BLOCKS_START),
            TaskDependency(c, a, DependencyType.BLOCKS_START),
        ]
    )
    cycle = graph.cycles()[0]
    assert cycle.task_ids == tuple(sorted((a, b, c)))


def test_self_dependency_is_a_cycle() -> None:
    task = TaskId(UUID(int=9))
    graph = DependencyGraph.from_dependencies(
        [TaskDependency(task, task, DependencyType.BLOCKS_START)]
    )
    assert graph.cycles()[0].task_ids == (task,)


def test_mixed_dependency_cycles_are_reported(task_ids) -> None:
    a, b, c = task_ids(3)
    graph = DependencyGraph.from_dependencies(
        [
            TaskDependency(a, b, DependencyType.BLOCKS_COMPLETION),
            TaskDependency(b, a, DependencyType.BLOCKS_START),
            TaskDependency(b, c, DependencyType.BLOCKS_START),
            TaskDependency(c, b, DependencyType.BLOCKS_COMPLETION),
        ]
    )
    # Blocks Completion participates in completion-feasibility cycle detection,
    # so a, b and c form one strongly connected component.
    members = {cycle.task_ids for cycle in graph.cycles()}
    assert members == {tuple(sorted((a, b, c)))}


def test_blocks_completion_does_not_constrain_starts(task_ids) -> None:
    a, b = task_ids(2)
    graph = DependencyGraph.from_dependencies(
        [TaskDependency(a, b, DependencyType.BLOCKS_COMPLETION)]
    )
    assert graph.start_predecessors(b) == frozenset()
    assert graph.completion_gates(b) == frozenset({a})


def test_start_edges_are_queryable(task_ids) -> None:
    a, b, c = task_ids(3)
    graph = DependencyGraph.from_dependencies(
        [
            TaskDependency(a, b, DependencyType.BLOCKS_START),
            TaskDependency(b, c, DependencyType.BLOCKS_START),
        ]
    )
    assert graph.cycles() == ()
    assert graph.start_predecessors(b) == frozenset({a})
    assert graph.start_successors(a) == frozenset({b})


def test_cycle_error_carries_paths(task_ids) -> None:
    a, b = task_ids(2)
    graph = DependencyGraph.from_dependencies(
        [
            TaskDependency(a, b, DependencyType.BLOCKS_START),
            TaskDependency(b, a, DependencyType.BLOCKS_START),
        ]
    )
    error = DependencyCycleError(graph.cycles())
    assert error.code == "DEPENDENCY_CYCLE"
    assert error.cycles[0].task_ids == tuple(sorted((a, b)))
