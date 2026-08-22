"""Authority policy table.

Prompt text, model confidence or any LLM output can never lower the level
required for an action class; the table below is the only source of truth.
"""

from personal_pm_planner.domain.enums import ActionType, AuthorizationLevel

AUTHORIZATION_POLICY: dict[ActionType, AuthorizationLevel] = {
    ActionType.CLASSIFY_INPUT: AuthorizationLevel.AUTOMATIC,
    ActionType.PRODUCE_DRAFT_PLAN: AuthorizationLevel.AUTOMATIC,
    ActionType.CALCULATE_PRIORITY: AuthorizationLevel.AUTOMATIC,
    ActionType.CREATE_LOW_HARM_TASK: AuthorizationLevel.AUTOMATIC_NOTIFY,
    ActionType.RESCHEDULE_LOW_RISK_TASK: AuthorizationLevel.AUTOMATIC_NOTIFY,
    ActionType.CREATE_FOCUS_BLOCK: AuthorizationLevel.APPROVAL,
    ActionType.CHANGE_SCOPE: AuthorizationLevel.APPROVAL,
    ActionType.CHANGE_HARD_DEADLINE: AuthorizationLevel.RECONFIRM,
    ActionType.CHANGE_FIXED_EVENT: AuthorizationLevel.RECONFIRM,
    ActionType.SEND_EXTERNAL_MESSAGE: AuthorizationLevel.RECONFIRM,
    ActionType.SUBMIT_EXTERNAL_ARTIFACT: AuthorizationLevel.RECONFIRM,
    ActionType.CANCEL_PROJECT: AuthorizationLevel.RECONFIRM,
    ActionType.IRREVERSIBLE_ACTION: AuthorizationLevel.RECONFIRM,
}


def authorization_level(action: ActionType) -> AuthorizationLevel:
    """Return the required authority level for *action*."""
    return AUTHORIZATION_POLICY[action]
