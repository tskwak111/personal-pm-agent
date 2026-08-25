from __future__ import annotations

from personal_pm_worker.briefings.generator import BriefingGenerator
from personal_pm_worker.briefings.schemas import BriefingContext


def _context(**overrides: object) -> BriefingContext:
    defaults: dict[str, object] = {
        "available_minutes": 240,
        "fixed_events": (("09:30 팀 회의", 60),),
        "core_outcome": "보고서 초안 완성",
        "must_do": (("보고서 초안", 90),),
        "risk_cards": (("HARD_DEADLINE 임박", "PLAN-004"),),
        "decision_requests": (),
        "planner_rule_ids": ("PLAN-001", "PLAN-004"),
        "missed_minutes": 0,
    }
    merged = {**defaults, **overrides}
    return BriefingContext(**merged)  # type: ignore[arg-type]


async def test_briefing_contains_only_planner_rule_ids() -> None:
    generator = BriefingGenerator()
    context = _context()
    result = await generator.generate_morning(context)
    assert set(result.reason_rule_ids) <= set(context.planner_rule_ids)


async def test_evening_copy_is_nonjudgmental() -> None:
    generator = BriefingGenerator()
    context = _context(missed_minutes=45)
    result = await generator.generate_evening(context)
    forbidden = {"실패", "게으름", "생산성이 낮"}
    assert not any(word in result.rendered_text for word in forbidden)


async def test_morning_includes_core_outcome_and_availability() -> None:
    generator = BriefingGenerator()
    result = await generator.generate_morning(_context())
    text = result.rendered_text
    assert "보고서 초안 완성" in text
    assert "240" in text


async def test_weekly_summary_uses_only_context_numbers() -> None:
    generator = BriefingGenerator()
    result = await generator.generate_weekly(_context(missed_minutes=120))
    assert "120" in result.rendered_text
