"""LLM gateway value types: requests, chunks and structured results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerifiedFact:
    subject: str
    predicate: str
    obj: str


@dataclass(frozen=True, slots=True)
class SourceChunk:
    text: str
    page_number: int | None
    block_index: int


@dataclass(frozen=True, slots=True)
class StructuredLLMRequest[T]:
    task_type: str
    prompt_version: str
    schema: type[T]
    verified_facts: tuple[VerifiedFact, ...]
    user_request: str
    untrusted_source_chunks: tuple[SourceChunk, ...]


@dataclass(frozen=True, slots=True)
class StructuredLLMResult[T]:
    value: T | None
    repair_count: int
    raw_response: str
