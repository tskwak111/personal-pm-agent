from __future__ import annotations

import pytest
from personal_pm_worker.llm.adapters.decomposition import (
    DecompositionResult,
    DecompositionTask,
    validate_decomposition,
)


def _scope(deliverable: str = "보고서 초안") -> object:
    from personal_pm_worker.llm.adapters.decomposition import ApprovedMilestoneScope

    return ApprovedMilestoneScope(milestone_id="m-1", deliverable=deliverable)


def _task(**overrides: object) -> DecompositionTask:
    defaults: dict[str, object] = {
        "title": "초안 작성",
        "base_duration_minutes": 60,
        "completion_conditions": ("개요 완성",),
        "depends_on": (),
        "outputs": ("outline.md",),
    }
    merged = {**defaults, **overrides}
    return DecompositionTask(**merged)  # type: ignore[arg-type]


def test_valid_decomposition_passes() -> None:
    result = DecompositionResult(
        deliverable="보고서 초안",
        tasks=(_task(), _task(title="자료 정리", base_duration_minutes=30)),
    )
    validate_decomposition(_scope(), result)  # must not raise


def test_decomposition_rejects_task_without_completion_condition() -> None:
    result = DecompositionResult(
        deliverable="보고서 초안",
        tasks=(_task(completion_conditions=()),),
    )
    with pytest.raises(Exception, match="COMPLETION"):
        validate_decomposition(_scope(), result)


def test_rejects_task_outside_30_120_minutes() -> None:
    small = DecompositionResult(
        deliverable="보고서 초안", tasks=(_task(base_duration_minutes=15),)
    )
    large = DecompositionResult(
        deliverable="보고서 초안", tasks=(_task(base_duration_minutes=180),)
    )
    with pytest.raises(Exception, match="SIZE"):
        validate_decomposition(_scope(), small)
    with pytest.raises(Exception, match="SIZE"):
        validate_decomposition(_scope(), large)


def test_cannot_expand_approved_deliverable() -> None:
    result = DecompositionResult(
        deliverable="전체 프로젝트 완성",
        tasks=(_task(),),
    )
    with pytest.raises(Exception, match="SCOPE"):
        validate_decomposition(_scope(), result)
