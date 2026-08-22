from personal_pm_planner.normalization.validate import normalize_and_validate


def test_done_task_with_remaining_minutes_is_invalid(planner_input_factory) -> None:
    value = planner_input_factory(done_task_remaining=15)
    result = normalize_and_validate(value)
    assert result.error_code == "INVALID_INPUT"
    assert "DONE_TASK_HAS_REMAINING_TIME" in result.rule_ids
    assert result.prior_plan_snapshot is None


def test_collection_order_does_not_change_hash(planner_input_factory) -> None:
    a = normalize_and_validate(planner_input_factory(reverse_tasks=False))
    b = normalize_and_validate(planner_input_factory(reverse_tasks=True))
    assert isinstance(a.input_hash, str)
    assert a.input_hash == b.input_hash
