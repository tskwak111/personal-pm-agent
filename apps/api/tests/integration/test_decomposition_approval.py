from __future__ import annotations

import pytest
from personal_pm_worker.llm.adapters.decomposition import (
    ApprovedMilestoneScope,
    DecompositionResult,
    DecompositionTask,
    InvalidTaskSizeError,
    MissingCompletionConditionError,
    ScopeExpansionError,
    validate_decomposition,
)


def test_decomposition_rejects_task_without_completion_condition() -> None:
    scope = ApprovedMilestoneScope(milestone_id="m-1", deliverable="보고서 초안")
    result = DecompositionResult(
        deliverable="보고서 초안",
        tasks=(
            DecompositionTask(
                title="초안 작성",
                base_duration_minutes=60,
                completion_conditions=(),
                depends_on=(),
                outputs=(),
            ),
        ),
    )
    with pytest.raises(MissingCompletionConditionError):
        validate_decomposition(scope, result)


def test_decomposition_cannot_expand_approved_deliverable() -> None:
    scope = ApprovedMilestoneScope(milestone_id="m-1", deliverable="보고서 초안")
    expanding = DecompositionResult(
        deliverable="프로젝트 전체 완료",
        tasks=(
            DecompositionTask(
                title="기타",
                base_duration_minutes=45,
                completion_conditions=("완료",),
                depends_on=(),
                outputs=(),
            ),
        ),
    )
    with pytest.raises(ScopeExpansionError):
        validate_decomposition(scope, expanding)


def test_task_size_bounds_are_enforced() -> None:
    scope = ApprovedMilestoneScope(milestone_id="m-1", deliverable="보고서 초안")

    def result(minutes: int) -> DecompositionResult:
        return DecompositionResult(
            deliverable="보고서 초안",
            tasks=(
                DecompositionTask(
                    title=f"task-{minutes}",
                    base_duration_minutes=minutes,
                    completion_conditions=("x",),
                    depends_on=(),
                    outputs=(),
                ),
            ),
        )

    with pytest.raises(InvalidTaskSizeError):
        validate_decomposition(scope, result(29))
    with pytest.raises(InvalidTaskSizeError):
        validate_decomposition(scope, result(121))
    validate_decomposition(scope, result(30))
    validate_decomposition(scope, result(120))
