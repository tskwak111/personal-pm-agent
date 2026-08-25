"""Document parser port and extraction value types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExtractionChunk:
    text: str
    page_number: int | None
    block_index: int
    bounding_box: tuple[float, float, float, float] | None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    chunks: tuple[ExtractionChunk, ...]
    parser_version: str


class DocumentParser(Protocol):
    async def parse(self, content: bytes, content_type: str) -> ExtractionResult: ...
