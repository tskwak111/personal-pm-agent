from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@dataclass(frozen=True, slots=True)
class DummySchema:
    title: str
    due_date: str | None = None


def _make_request() -> Any:
    from personal_pm_worker.llm.schemas import (
        SourceChunk,
        StructuredLLMRequest,
        VerifiedFact,
    )

    fact = VerifiedFact(subject="user", predicate="has_course", obj="CS101")
    chunk = SourceChunk(text="CS101 due Friday", page_number=1, block_index=0)
    return StructuredLLMRequest(
        task_type="intake_structuring",
        prompt_version="intake-structuring-v1",
        schema=DummySchema,
        verified_facts=(fact,),
        user_request="extract deadlines",
        untrusted_source_chunks=(chunk,),
    )


async def test_untrusted_content_is_separate_from_policy() -> None:
    from personal_pm_worker.llm.fake import FakeLLMGateway

    gateway = FakeLLMGateway()
    request = _make_request()
    await gateway.generate_structured(request)
    rendered = gateway.last_rendered_request
    assert rendered is not None
    assert "UNTRUSTED_SOURCE_CONTENT" in rendered
    assert "SYSTEM_POLICY" in rendered
    assert rendered.index("SYSTEM_POLICY") < rendered.index("UNTRUSTED_SOURCE_CONTENT")


async def test_invalid_first_response_gets_one_repair() -> None:
    from personal_pm_worker.llm.fake import FakeLLMGateway

    gateway = FakeLLMGateway()
    request = _make_request()

    # First raw response violates the schema (missing required title);
    # second one is valid → exactly one bounded repair.
    gateway.enqueue_raw('{"due_date": "2026-09-01"}')
    gateway.enqueue_raw('{"title": "CS101 homework", "due_date": "2026-09-01"}')

    result = await gateway.generate_structured(request)
    assert result.repair_count == 1
    assert result.value is not None
    assert result.value.title == "CS101 homework"


async def test_two_invalid_responses_fail_typed() -> None:
    from personal_pm_worker.llm.fake import FakeLLMGateway
    from personal_pm_worker.llm.gateway import StructuredLLMError

    gateway = FakeLLMGateway()
    gateway.enqueue_raw('{"nope": 1}')
    gateway.enqueue_raw('{"still_bad": true}')

    with pytest.raises(StructuredLLMError):
        await gateway.generate_structured(_make_request())


async def test_prompt_versions_are_pinned_in_request() -> None:
    from personal_pm_worker.llm.fake import FakeLLMGateway
    from personal_pm_worker.llm.prompts import get_prompt_template

    template = get_prompt_template("intake-structuring-v1")
    assert "UNTRUSTED_SOURCE_CONTENT" in template
    assert "SYSTEM_POLICY" in template

    gateway = FakeLLMGateway()
    await gateway.generate_structured(_make_request())
    assert gateway.last_prompt_version == "intake-structuring-v1"
