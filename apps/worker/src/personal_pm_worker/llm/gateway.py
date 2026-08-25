"""Provider-independent structured LLM gateway with one bounded repair."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from personal_pm_worker.llm.errors import PromptNotFoundError, StructuredLLMError
from personal_pm_worker.llm.prompts import get_prompt_template
from personal_pm_worker.llm.schemas import StructuredLLMRequest, StructuredLLMResult


class ProviderAdapter(Protocol):
    async def complete(self, rendered_prompt: str) -> str: ...


REPAIR_SUFFIX = (
    "\nSYSTEM_POLICY:\nThe previous response was invalid JSON or missing "
    "required fields. Respond again with valid JSON only."
)


def render_request(request: StructuredLLMRequest[Any]) -> str:
    template = get_prompt_template(request.prompt_version)
    chunks = "\n---\n".join(
        f"[page={chunk.page_number} block={chunk.block_index}] {chunk.text}"
        for chunk in request.untrusted_source_chunks
    )
    facts = "\n".join(
        f"- {fact.subject} {fact.predicate} {fact.obj}"
        for fact in request.verified_facts
    ) or "(none)"
    return template.format(
        user_request=request.user_request,
        verified_facts=facts,
        source_chunks=chunks,
    )


def _validate(raw: str, schema: type[Any]) -> Any:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("response is not a JSON object")
    fields = getattr(schema, "__dataclass_fields__", {})
    required = set(fields.keys())
    if required:
        missing = required - set(parsed.keys())
        if missing:
            raise ValueError(f"missing fields: {sorted(missing)}")
    for name in required & set(parsed.keys()):
        value = parsed[name]
        expected = getattr(fields[name].type, "__name__", str(fields[name].type))
        if expected == "str" and not isinstance(value, str):
            raise ValueError(f"field {name} must be str")
        if "NoneType" in str(fields[name].type) and value is not None:
            if expected == "str" or "str" in str(fields[name].type):
                if not isinstance(value, str):
                    raise ValueError(f"field {name} must be str or null")
    return schema(**parsed)


T = TypeVar("T")


@dataclass
class LLMGateway(Generic[T]):
    adapter: ProviderAdapter

    async def generate_structured(
        self, request: StructuredLLMRequest[T]
    ) -> StructuredLLMResult[T]:
        rendered = render_request(request)
        raw_first = await self.adapter.complete(rendered)
        try:
            value = _validate(raw_first, request.schema)
            return StructuredLLMResult(value=value, repair_count=0, raw_response=raw_first)
        except (ValueError, TypeError):
            pass

        # Exactly one bounded repair.
        raw_second = await self.adapter.complete(rendered + REPAIR_SUFFIX)
        try:
            value = _validate(raw_second, request.schema)
        except (ValueError, TypeError) as exc:
            raise StructuredLLMError(f"repair failed: {exc}") from exc
        return StructuredLLMResult(value=value, repair_count=1, raw_response=raw_second)


def validate_or_repair_once(
    raw_first: str,
    schema: type[Any],
    repaired_raw: str | None,
) -> tuple[Any | None, int]:
    """Pure helper used by tests and adapters; returns (value, repair_count)."""
    try:
        return _validate(raw_first, schema), 0
    except (ValueError, TypeError):
        pass
    if repaired_raw is None:
        raise StructuredLLMError("no repair response available")
    try:
        return _validate(repaired_raw, schema), 1
    except (ValueError, TypeError) as exc:
        raise StructuredLLMError(f"repair failed: {exc}") from exc


__all__ = [
    "LLMGateway",
    "PromptNotFoundError",
    "StructuredLLMError",
    "ProviderAdapter",
    "render_request",
    "validate_or_repair_once",
]
