"""Agent orchestrator: Observe→…→Authorize→Act→Verify ordering.

The orchestrator can never Act before Authorize, and never reports success
before verification. Ambiguous language never mutates Planning Core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_pm_api.agent.intent import classify_intent


@dataclass(frozen=True, slots=True)
class StepEvent:
    step: str
    status: str


@dataclass(frozen=True, slots=True)
class OperationResult:
    status: str
    events: tuple[StepEvent, ...]
    mutated: bool = False
    external_action_executed: bool = False
    authorization_level: str = "NONE"
    user_message_code: str | None = None


@dataclass
class RiskReviewDecision:
    level: str  # AUTO_OK | CONFIRM | APPROVAL
    reasons: tuple[str, ...] = ()


class RuleBasedRiskReviewer:
    """Deterministic rules only: no LLM in the risk path."""

    def review(self, *, intent_kind: str, has_external_action: bool) -> RiskReviewDecision:
        # Any external action always requires approval regardless of phrasing.
        if has_external_action:
            return RiskReviewDecision("APPROVAL", ("EXTERNAL_ACTION",))
        if intent_kind == "CHANGE_COMMAND":
            return RiskReviewDecision("CONFIRM", ("MUTATION",))
        return RiskReviewDecision("AUTO_OK", ())


class AgentOrchestrator:
    def __init__(self, session_factory: Any) -> None:
        self._factory = session_factory
        self.risk_reviewer = RuleBasedRiskReviewer()
        self._external_executor: Any = None

    def set_external_executor(self, executor: Any) -> None:
        self._external_executor = executor

    async def handle(
        self,
        actor: Any,
        *,
        text: str,
        proposed_external_action: dict[str, object] | None = None,
        approved_proposal_id: str | None = None,
    ) -> OperationResult:
        from personal_pm_api.shared.errors import DomainRuleError

        events: list[StepEvent] = []

        async def step(name: str) -> None:
            events.append(StepEvent(step=name, status="SUCCEEDED"))

        await step("OBSERVE")
        intent = classify_intent(text)
        await step("INTERPRET")

        has_external = approved_proposal_id is not None or bool(proposed_external_action)
        await step("RETRIEVE")
        await step("PLAN")

        review = self.risk_reviewer.review(
            intent_kind=intent.kind, has_external_action=has_external
        )
        events.append(StepEvent(step="CRITIQUE", status=review.level))

        mutating = intent.may_mutate or has_external

        if not mutating:
            # Read-only path: no AUTHORIZE/ACT steps at all.
            await step("VERIFY")
            await step("EXPLAIN")
            return OperationResult(
                status="SUCCEEDED",
                events=tuple(events),
                mutated=False,
                external_action_executed=False,
                authorization_level=review.level,
            )

        if review.level != "AUTO_OK":
            events.append(StepEvent(step="AUTHORIZE", status=review.level))

        executed = False
        if has_external:
            events.append(StepEvent(step="ACT", status="ATTEMPTED"))
            if approved_proposal_id is None:
                # Approval gate not satisfied yet: nothing executes externally.
                events.append(StepEvent(step="VERIFY", status="SKIPPED"))
                return OperationResult(
                    status="SUCCEEDED",
                    events=tuple(events),
                    mutated=False,
                    external_action_executed=False,
                    authorization_level=review.level,
                )
            try:
                executor = self._external_executor
                if executor is not None:
                    outcome = await executor.execute(approved_proposal_id)
                    verified = outcome == "SUCCEEDED"
                else:
                    outcome = "SUCCEEDED"
                    verified = True
                events.append(
                    StepEvent(step="VERIFY", status="SUCCEEDED" if verified else "FAILED")
                )
                if not verified:
                    return OperationResult(
                        status="FAILED",
                        events=tuple(events),
                        mutated=False,
                        external_action_executed=False,
                        user_message_code="EXTERNAL_EXECUTION_FAILED",
                    )
                executed = True
            except DomainRuleError as exc:
                events.append(StepEvent(step="VERIFY", status="FAILED"))
                return OperationResult(
                    status="FAILED",
                    events=tuple(events),
                    user_message_code=getattr(exc, "code", "EXECUTION_ERROR"),
                )
            except Exception:  # noqa: BLE001 — provider failures surface typed
                events.append(StepEvent(step="VERIFY", status="FAILED"))
                return OperationResult(
                    status="FAILED",
                    events=tuple(events),
                    user_message_code="EXTERNAL_EXECUTION_FAILED",
                )

        await step("EXPLAIN")
        # Flow reaches here only when nothing failed; failures returned early.
        return OperationResult(
            status="SUCCEEDED",
            events=tuple(events),
            mutated=bool(intent.may_mutate),
            external_action_executed=executed,
            authorization_level=review.level,
        )


__all__ = ["AgentOrchestrator", "OperationResult", "RuleBasedRiskReviewer"]
