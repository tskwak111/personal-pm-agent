"""Overload negotiation proposals in the normative order."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from personal_pm_planner.domain.enums import AuthorizationLevel
from personal_pm_planner.domain.identifiers import MilestoneId, TaskId


@dataclass(frozen=True, slots=True)
class Proposal:
    proposal_id: str
    kind: str
    approval_level: AuthorizationLevel
    affected_task_ids: tuple[TaskId, ...]
    milestone_id: MilestoneId | None
    minutes_saved_or_added: int
    reason_rule_id: str


def proposal_id_for(kind: str, seed: TaskId | MilestoneId) -> str:
    return str(uuid5(NAMESPACE_URL, f"proposal:{kind}:{seed.value.hex}"))


def proposal_for_disallowed_move(
    task_id: TaskId,
    *,
    reason_rule_id: str,
    milestone_id: MilestoneId | None,
    minutes_delta: int,
) -> Proposal:
    """A protected item would have to move: user approval is required."""
    return Proposal(
        proposal_id=proposal_id_for("DISALLOWED_MOVE", task_id),
        kind="DISALLOWED_MOVE_REQUIRED",
        approval_level=AuthorizationLevel.APPROVAL,
        affected_task_ids=(task_id,),
        milestone_id=milestone_id,
        minutes_saved_or_added=minutes_delta,
        reason_rule_id=reason_rule_id,
    )


def overload_proposal_sequence(
    *,
    optional_task_ids: tuple[TaskId, ...],
    deferrable_task_ids: tuple[TaskId, ...],
    scope_reducible_milestone_ids: tuple[MilestoneId, ...] = (),
    external_negotiation_available: bool = False,
    extra_hours_allowed: bool = False,
    cancellable_project_available: bool = False,
) -> list[Proposal]:
    """Ordered overload candidates per Planner Spec section 15.

    Removal precedes deferral, scope reduction, external negotiation and extra
    labor; cancellation comes last. Sleep/class/recovery time is never offered.
    """
    sequence: list[Proposal] = []

    def add(kind: str, ids: tuple[TaskId, ...], level: AuthorizationLevel, rule: str) -> None:
        if not ids:
            return
        sequence.append(
            Proposal(
                proposal_id=proposal_id_for(kind, ids[0]),
                kind=kind,
                approval_level=level,
                affected_task_ids=ids,
                milestone_id=None,
                minutes_saved_or_added=0,
                reason_rule_id=rule,
            )
        )

    add(
        "REMOVE_OPTIONAL",
        optional_task_ids,
        AuthorizationLevel.AUTOMATIC_NOTIFY,
        "OVERLOAD_STEP_REMOVE_P4",
    )
    add(
        "DEFER_FLEXIBLE",
        deferrable_task_ids,
        AuthorizationLevel.APPROVAL,
        "OVERLOAD_STEP_DEFER_P3_LOW_P2",
    )
    if scope_reducible_milestone_ids:
        sequence.append(
            Proposal(
                proposal_id=proposal_id_for("SCOPE_REDUCTION", scope_reducible_milestone_ids[0]),
                kind="SCOPE_REDUCTION",
                approval_level=AuthorizationLevel.APPROVAL,
                affected_task_ids=(),
                milestone_id=scope_reducible_milestone_ids[0],
                minutes_saved_or_added=0,
                reason_rule_id="OVERLOAD_STEP_SCOPE_REDUCTION",
            )
        )
    if external_negotiation_available:
        sentinel = TaskId(UUID(int=0))
        sequence.append(
            Proposal(
                proposal_id=proposal_id_for("EXTERNAL_NEGOTIATION", sentinel),
                kind="EXTERNAL_NEGOTIATION",
                approval_level=AuthorizationLevel.RECONFIRM,
                affected_task_ids=(),
                milestone_id=None,
                minutes_saved_or_added=0,
                reason_rule_id="OVERLOAD_STEP_EXTERNAL_NEGOTIATION",
            )
        )
    if extra_hours_allowed:
        sequence.append(
            Proposal(
                proposal_id=proposal_id_for("EXTRA_HOURS", TaskId(UUID(int=0))),
                kind="LIMITED_EXTRA_HOURS",
                approval_level=AuthorizationLevel.APPROVAL,
                affected_task_ids=(),
                milestone_id=None,
                minutes_saved_or_added=0,
                reason_rule_id="OVERLOAD_STEP_LIMITED_EXTRA_TIME",
            )
        )
    if cancellable_project_available:
        sequence.append(
            Proposal(
                proposal_id=proposal_id_for("PROJECT_CANCEL_REVIEW", TaskId(UUID(int=0))),
                kind="PROJECT_CANCEL_REVIEW",
                approval_level=AuthorizationLevel.RECONFIRM,
                affected_task_ids=(),
                milestone_id=None,
                minutes_saved_or_added=0,
                reason_rule_id="OVERLOAD_STEP_CANCEL_REVIEW",
            )
        )
    return sequence


__all__ = ["Proposal", "overload_proposal_sequence", "proposal_for_disallowed_move"]
