"""Task dependency contracts with deterministic cycle detection.

`Blocks Start` constrains scheduling starts; `Blocks Completion` only gates
the Done transition. Cycle detection runs over both graphs so completion
infeasibility is reported even when starts remain possible.
"""

from dataclasses import dataclass
from uuid import UUID

from personal_pm_planner.domain.enums import DependencyType
from personal_pm_planner.domain.identifiers import TaskId

_CYCLE_EDGES = frozenset({DependencyType.BLOCKS_START, DependencyType.BLOCKS_COMPLETION})


def _sort_key(task_id: TaskId) -> str:
    return task_id.value.hex


@dataclass(frozen=True, slots=True)
class TaskDependency:
    predecessor_id: TaskId
    successor_id: TaskId
    dependency_type: DependencyType


@dataclass(frozen=True, slots=True)
class DependencyCycle:
    task_ids: tuple[TaskId, ...]


class DependencyGraph:
    """Immutable view over task dependencies."""

    __slots__ = ("dependencies",)

    def __init__(self, dependencies: tuple[TaskDependency, ...]) -> None:
        self.dependencies = tuple(
            sorted(
                dependencies,
                key=lambda item: (
                    _sort_key(item.predecessor_id),
                    _sort_key(item.successor_id),
                    item.dependency_type.value,
                ),
            )
        )

    @classmethod
    def from_dependencies(
        cls, dependencies: list[TaskDependency] | tuple[TaskDependency, ...]
    ) -> "DependencyGraph":
        seen: set[tuple[str, str, str]] = set()
        for item in dependencies:
            key = (
                _sort_key(item.predecessor_id),
                _sort_key(item.successor_id),
                item.dependency_type.value,
            )
            if key in seen:
                raise ValueError(f"duplicate dependency: {key}")
            if item.predecessor_id.value == UUID(int=0):
                raise ValueError("nil predecessor id")
        return cls(tuple(dependencies))

    def cycles(self) -> tuple[DependencyCycle, ...]:
        adjacency = self._cycle_adjacency()
        components = _strongly_connected_components(adjacency)
        cycles: list[DependencyCycle] = []
        for component in components:
            if len(component) > 1 or any(
                successor is member or successor == member
                for member in component
                for successor in adjacency.get(member, ())
            ):
                ordered = tuple(sorted(component, key=_sort_key))
                cycles.append(DependencyCycle(task_ids=ordered))
        cycles.sort(key=lambda cycle: _sort_key(cycle.task_ids[0]))
        return tuple(cycles)

    def start_predecessors(self, task_id: TaskId) -> frozenset[TaskId]:
        return frozenset(
            item.predecessor_id
            for item in self.dependencies
            if item.successor_id == task_id and item.dependency_type is DependencyType.BLOCKS_START
        )

    def start_successors(self, task_id: TaskId) -> frozenset[TaskId]:
        return frozenset(
            item.successor_id
            for item in self.dependencies
            if item.predecessor_id == task_id
            and item.dependency_type is DependencyType.BLOCKS_START
        )

    def completion_gates(self, task_id: TaskId) -> frozenset[TaskId]:
        return frozenset(
            item.predecessor_id
            for item in self.dependencies
            if item.successor_id == task_id
            and item.dependency_type is DependencyType.BLOCKS_COMPLETION
        )

    def _cycle_adjacency(self) -> dict[TaskId, set[TaskId]]:
        adjacency: dict[TaskId, set[TaskId]] = {}
        for item in self.dependencies:
            if item.dependency_type not in _CYCLE_EDGES:
                continue
            adjacency.setdefault(item.predecessor_id, set()).add(item.successor_id)
            adjacency.setdefault(item.successor_id, set())
        return adjacency


def _strongly_connected_components(
    adjacency: dict[TaskId, set[TaskId]],
) -> list[tuple[TaskId, ...]]:
    """Iterative Tarjan SCC over deterministically ordered nodes."""
    index_counter = 0
    indices: dict[TaskId, int] = {}
    lowlink: dict[TaskId, int] = {}
    stack: list[TaskId] = []
    on_stack: set[TaskId] = set()
    components: list[tuple[TaskId, ...]] = []

    def next_index() -> int:
        nonlocal index_counter
        value = index_counter
        index_counter += 1
        return value

    for root in sorted(adjacency, key=_sort_key):
        if root in indices:
            continue
        work: list[tuple[TaskId, list[TaskId], int]] = []
        indices[root] = lowlink[root] = next_index()
        stack.append(root)
        on_stack.add(root)
        work.append((root, sorted(adjacency[root], key=_sort_key), 0))
        while work:
            node, successors, pointer = work.pop()
            advanced = False
            while pointer < len(successors):
                successor = successors[pointer]
                pointer += 1
                if successor not in indices:
                    work.append((node, successors, pointer))
                    indices[successor] = lowlink[successor] = next_index()
                    stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, sorted(adjacency[successor], key=_sort_key), 0))
                    advanced = True
                    break
                if successor in on_stack:
                    lowlink[node] = min(lowlink[node], indices[successor])
            if advanced:
                continue
            if lowlink[node] == indices[node]:
                component: list[TaskId] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(tuple(component))
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
    return components
