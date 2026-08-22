from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from personal_pm_planner.domain.approval import Approval, ApprovalTarget
from personal_pm_planner.domain.audit import AuditEvent
from personal_pm_planner.domain.authorization import authorization_level
from personal_pm_planner.domain.enums import ActionType, AuthorizationLevel
from personal_pm_planner.domain.identifiers import WorkspaceId

WORKSPACE = WorkspaceId(UUID("00000000-0000-0000-0000-000000000001"))
NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def test_hard_deadline_change_requires_reconfirmation() -> None:
    assert authorization_level(ActionType.CHANGE_HARD_DEADLINE) is AuthorizationLevel.RECONFIRM


def test_priority_calculation_is_automatic() -> None:
    assert authorization_level(ActionType.CALCULATE_PRIORITY) is AuthorizationLevel.AUTOMATIC


def test_authority_matrix_levels() -> None:
    assert authorization_level(ActionType.CREATE_FOCUS_BLOCK) is AuthorizationLevel.APPROVAL
    assert (
        authorization_level(ActionType.RESCHEDULE_LOW_RISK_TASK)
        is AuthorizationLevel.AUTOMATIC_NOTIFY
    )
    assert authorization_level(ActionType.SEND_EXTERNAL_MESSAGE) is AuthorizationLevel.RECONFIRM
    assert authorization_level(ActionType.CHANGE_FIXED_EVENT) is AuthorizationLevel.RECONFIRM


def test_policy_covers_every_action_type() -> None:
    covered = set(AUTHORIZATION_POLICY_KEYS())
    assert covered == set(ActionType)


def AUTHORIZATION_POLICY_KEYS() -> set[ActionType]:
    from personal_pm_planner.domain.authorization import AUTHORIZATION_POLICY

    return set(AUTHORIZATION_POLICY)


def make_approval(**overrides: object) -> Approval:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": WORKSPACE,
        "actor_user_id": UUID("00000000-0000-0000-0000-0000000000aa"),
        "proposal_id": UUID("00000000-0000-0000-0000-0000000000bb"),
        "proposal_version": 3,
        "action_type": ActionType.CHANGE_HARD_DEADLINE,
        "command_hash": "abc123",
        "targets": (ApprovalTarget(object_kind="milestone", object_id="m-1", expected_version=5),),
        "granted_at": NOW,
        "expires_at": NOW + timedelta(hours=1),
    }
    defaults.update(overrides)
    return Approval(**defaults)  # type: ignore[arg-type]


def test_approval_accepts_matching_binding() -> None:
    approval = make_approval()
    approval.validate_use(
        now=NOW + timedelta(minutes=1),
        proposal_version=3,
        command_hash="abc123",
        targets=(ApprovalTarget(object_kind="milestone", object_id="m-1", expected_version=5),),
        workspace_id=WORKSPACE,
        action_type=ActionType.CHANGE_HARD_DEADLINE,
    )


def test_changed_target_version_invalidates_approval() -> None:
    approval = make_approval()
    with pytest.raises(ValueError, match="stale"):
        approval.validate_use(
            now=NOW + timedelta(minutes=1),
            proposal_version=3,
            command_hash="abc123",
            targets=(ApprovalTarget(object_kind="milestone", object_id="m-1", expected_version=6),),
            workspace_id=WORKSPACE,
            action_type=ActionType.CHANGE_HARD_DEADLINE,
        )


def test_expired_approval_is_invalid() -> None:
    approval = make_approval()
    with pytest.raises(ValueError, match="expired"):
        approval.validate_use(
            now=NOW + timedelta(hours=2),
            proposal_version=3,
            command_hash="abc123",
            targets=(ApprovalTarget(object_kind="milestone", object_id="m-1", expected_version=5),),
            workspace_id=WORKSPACE,
            action_type=ActionType.CHANGE_HARD_DEADLINE,
        )


def test_workspace_mismatch_is_rejected() -> None:
    approval = make_approval()
    other = WorkspaceId(UUID("00000000-0000-0000-0000-000000000002"))
    with pytest.raises(ValueError, match="workspace"):
        approval.validate_use(
            now=NOW,
            proposal_version=3,
            command_hash="abc123",
            targets=(ApprovalTarget(object_kind="milestone", object_id="m-1", expected_version=5),),
            workspace_id=other,
            action_type=ActionType.CHANGE_HARD_DEADLINE,
        )


def test_audit_event_requires_reason_trace_and_aware_time() -> None:
    with pytest.raises(ValueError, match="reason"):
        _make_audit(reason="   ")
    with pytest.raises(ValueError, match="trace"):
        _make_audit(trace_id="")
    with pytest.raises(ValueError, match="timezone-aware"):
        _make_audit(occurred_at=datetime(2026, 8, 23, 12, 0))


def _make_audit(**overrides: object) -> AuditEvent:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "workspace_id": WORKSPACE,
        "actor_user_id": UUID("00000000-0000-0000-0000-0000000000aa"),
        "entity_kind": "task",
        "entity_id": "t-1",
        "before_state": '{"status":"ready"}',
        "after_state": '{"status":"in_progress"}',
        "reason": "user started a session",
        "rule_basis": ("SM-1",),
        "approval_id": None,
        "trace_id": "trace-1",
        "reversible": True,
        "occurred_at": NOW,
    }
    defaults.update(overrides)
    return AuditEvent(**defaults)  # type: ignore[arg-type]
