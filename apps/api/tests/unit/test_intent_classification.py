from __future__ import annotations

from personal_pm_api.agent.intent import classify_intent


def test_conditional_language_is_review_not_command() -> None:
    result = classify_intent("논문 정리를 다음 주로 미루면 어떨까?")
    assert result.kind == "REVIEW_REQUEST"
    assert result.may_mutate is False


def test_direct_imperative_is_change_command() -> None:
    result = classify_intent("논문 정리를 다음 주로 미뤄")
    assert result.kind == "CHANGE_COMMAND"
    assert result.may_mutate is True


def test_plain_question_is_informational() -> None:
    result = classify_intent("오늘 남은 일정이 뭐야?")
    assert result.may_mutate is False


def test_unknown_language_defaults_to_ambiguous() -> None:
    result = classify_intent("그냥 그렇네")
    assert result.kind == "AMBIGUOUS"
    assert result.may_mutate is False


def test_review_marker_beats_command_marker() -> None:
    # Both present: the safe interpretation (review) must win.
    result = classify_intent("미뤄볼까 검토해줘")
    assert result.kind == "REVIEW_REQUEST"
    assert result.may_mutate is False
