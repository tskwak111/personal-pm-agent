"""Deterministic fake LLM gateway for tests and local runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from personal_pm_worker.llm.gateway import LLMGateway
from personal_pm_worker.llm.schemas import StructuredLLMRequest, StructuredLLMResult


@dataclass
class _ScriptedAdapter:
    """Returns scripted raw responses in order; records rendered prompts."""

    responses: list[str] = field(default_factory=list)
    rendered_prompts: list[str] = field(default_factory=list)

    async def complete(self, rendered_prompt: str) -> str:
        self.rendered_prompts.append(rendered_prompt)
        if not self.responses:
            raise AssertionError("FakeLLMGateway ran out of scripted responses")
        return self.responses.pop(0)


@dataclass
class FakeLLMGateway:
    """Scripted gateway: deterministic outputs, no network, full prompt capture."""

    adapter: _ScriptedAdapter = field(default_factory=_ScriptedAdapter)

    def __post_init__(self) -> None:
        # Rebuild the gateway facade over the scripted adapter.
        object.__setattr__(self, "_gateway", LLMGateway(adapter=self.adapter))

    def enqueue_raw(self, raw_response: str) -> None:
        self.adapter.responses.append(raw_response)

    @property
    def last_rendered_request(self) -> str | None:
        if not self.adapter.rendered_prompts:
            return None
        return self.adapter.rendered_prompts[0]

    @property
    def last_prompt_version(self) -> str | None:
        return "intake-structuring-v1"

    async def generate_structured(
        self, request: StructuredLLMRequest[Any]
    ) -> StructuredLLMResult[Any]:
        # Deterministic default when the caller scripted no responses:
        # emit a schema-shaped JSON object with placeholder values.
        if not self.adapter.responses:
            fields = getattr(request.schema, "__dataclass_fields__", {})
            payload = {
                name: ("placeholder" if "str" in str(info.type) else None)
                for name, info in fields.items()
            }
            self.adapter.responses.append(json.dumps(payload, ensure_ascii=False))
        result: StructuredLLMResult[Any] = await self._gateway.generate_structured(request)  # type: ignore[attr-defined]
        return result

    def dump_script(self) -> str:
        return json.dumps(self.adapter.responses, ensure_ascii=False)
