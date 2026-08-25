"""Evidence-grounded briefing generation.

Reasons are a strict subset of verified Planner rule ids; language is
nonjudgmental and only uses numbers present in the context.
"""

from __future__ import annotations

from personal_pm_worker.briefings.schemas import BriefingContext, BriefingResult

FORBIDDEN_JUDGMENT_WORDS = ("실패", "게으름", "생산성이 낮", "지연됐다", "부족하다")


def _sanitize(text: str) -> str:
    return text


class BriefingGenerator:
    async def generate_morning(self, context: BriefingContext) -> BriefingResult:
        lines = [
            "아침 브리핑",
            f"오늘 가용 시간: {context.available_minutes}분",
            "핵심 성과 목표: " + context.core_outcome,
        ]
        if context.fixed_events:
            lines.append("고정 일정:")
            lines.extend(f"- {name} ({minutes}분)" for name, minutes in context.fixed_events)
        if context.must_do:
            lines.append("반드시 할 일:")
            lines.extend(f"- {name} ({minutes}분)" for name, minutes in context.must_do)
        if context.risk_cards:
            lines.append("주의 카드:")
            lines.extend(f"- {label}" for label, _rule in context.risk_cards)
        text = _sanitize("\n".join(lines))
        assert not any(word in text for word in FORBIDDEN_JUDGMENT_WORDS)
        return BriefingResult(
            rendered_text=text,
            reason_rule_ids=tuple(context.planner_rule_ids),
        )

    async def generate_evening(self, context: BriefingContext) -> BriefingResult:
        remaining = context.missed_minutes
        lines = [
            "저녁 정리",
            f"계획 대비 남은 시간: {remaining}분",
            "남은 항목은 내일 계획으로 이동했습니다.",
        ]
        text = _sanitize("\n".join(lines))
        # Nonjudgmental contract: never blame the user.
        assert not any(word in text for word in FORBIDDEN_JUDGMENT_WORDS)
        return BriefingResult(
            rendered_text=text,
            reason_rule_ids=tuple(context.planner_rule_ids),
        )

    async def generate_weekly(self, context: BriefingContext) -> BriefingResult:
        lines = [
            "주간 요약",
            f"이번 주 미완료 시간: {context.missed_minutes}분",
            f"다음 주 가용 시간 기준: {context.available_minutes}분",
        ]
        text = _sanitize("\n".join(lines))
        assert not any(word in text for word in FORBIDDEN_JUDGMENT_WORDS)
        return BriefingResult(
            rendered_text=text,
            reason_rule_ids=tuple(context.planner_rule_ids),
        )


__all__ = ["BriefingGenerator"]
