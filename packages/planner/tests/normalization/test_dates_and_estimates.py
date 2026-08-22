from datetime import UTC, datetime


def test_date_only_deadline_uses_conservative_boundary_without_changing_fact(
    date_only_milestone,
) -> None:
    from personal_pm_planner.normalization.dates import effective_deadline

    result = effective_deadline(date_only_milestone, "Asia/Seoul")
    assert result.assumption == "DATE_ONLY_START_OF_DAY"
    assert result.instant is not None
    # 2026-09-10 00:00 Asia/Seoul == 2026-09-09 15:00 UTC
    assert result.instant == datetime(2026, 9, 9, 15, 0, tzinfo=UTC)
    # The original fact remains untouched.
    assert date_only_milestone.deadline_at is None
    assert date_only_milestone.deadline_time_known is False


def test_verified_instant_is_used_directly(milestone_factory) -> None:
    from personal_pm_planner.normalization.dates import effective_deadline

    instant = datetime(2026, 9, 10, 23, 59, tzinfo=UTC)
    milestone = milestone_factory(deadline_at=instant, deadline_time_known=True)
    result = effective_deadline(milestone, "Asia/Seoul")
    assert result.assumption == "VERIFIED_INSTANT"
    assert result.instant == instant


def test_missing_deadline_is_reported_not_invented(milestone_factory) -> None:
    from personal_pm_planner.normalization.dates import effective_deadline

    milestone = milestone_factory(deadline_date=None, deadline_date_known=False)
    result = effective_deadline(milestone, "Asia/Seoul")
    assert result.instant is None
    assert result.assumption == "NO_DEADLINE"


def test_high_uncertainty_uses_160_percent_and_slot_rounding() -> None:
    from personal_pm_planner.normalization.estimates import derive_estimate

    result = derive_estimate(raw_base_minutes=61, factor=1.0, uncertainty="high", slot_minutes=15)
    assert result.base_minutes == 75
    assert result.safety_minutes == 120


def test_estimation_factor_is_clamped_to_policy_bounds() -> None:

    from personal_pm_planner.normalization.estimates import derive_estimate

    fast = derive_estimate(raw_base_minutes=60, factor=0.10, uncertainty="low", slot_minutes=15)
    slow = derive_estimate(raw_base_minutes=60, factor=99.0, uncertainty="low", slot_minutes=15)
    assert fast.base_minutes == 45  # clamped to 0.75
    assert slow.base_minutes == 150  # clamped to 2.50
    assert fast.safety_minutes >= fast.base_minutes
    assert slow.safety_minutes >= slow.base_minutes


def test_sample_strength_blends_observed_factor() -> None:
    import pytest
    from personal_pm_planner.normalization.estimates import blended_factor

    assert blended_factor(observed=1.5, sample_count=2) == pytest.approx(1.0)
    assert blended_factor(observed=2.0, sample_count=4) == pytest.approx(1.30)
    assert blended_factor(observed=2.0, sample_count=10) == pytest.approx(1.60)
    assert blended_factor(observed=2.0, sample_count=25) == pytest.approx(1.80)


def test_safety_never_below_base_for_low_uncertainty_rounding() -> None:
    from personal_pm_planner.normalization.estimates import derive_estimate

    result = derive_estimate(raw_base_minutes=14, factor=1.0, uncertainty="low", slot_minutes=15)
    assert result.base_minutes == 15
    assert result.safety_minutes >= result.base_minutes
