"""Versioned extraction pipeline: same source+parser version reuses results."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from personal_pm_worker.files.parsers import DocumentParser, ExtractionResult
from personal_pm_worker.files.storage import ObjectStorage


@dataclass(frozen=True, slots=True)
class ExtractionRecord:
    id: str
    source_key: str
    parser_version: str
    result: ExtractionResult


@dataclass
class ExtractionPipeline:
    storage: ObjectStorage
    parser: DocumentParser
    _cache: dict[str, ExtractionRecord] = field(default_factory=dict)

    async def extract(self, source_key: str, *, parser_version: str) -> Any:
        cache_key = self._cache_key(source_key, parser_version)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        content = await self.storage.get(source_key)
        content_type = self._guess_content_type(source_key)
        parsed = await self.parser.parse(content, content_type)
        record = ExtractionRecord(
            id=self._record_id(source_key, parser_version),
            source_key=source_key,
            parser_version=parser_version,
            result=parsed,
        )
        self._cache[cache_key] = record
        return record

    def _cache_key(self, source_key: str, parser_version: str) -> str:
        return f"{source_key}::{parser_version}"

    @staticmethod
    def _record_id(source_key: str, parser_version: str) -> str:
        digest = hashlib.sha256(f"{source_key}::{parser_version}".encode()).hexdigest()
        return digest[:32]

    @staticmethod
    def _guess_content_type(source_key: str) -> str:
        lowered = source_key.lower()
        if lowered.endswith(".pdf"):
            return "application/pdf"
        if lowered.endswith(".txt") or lowered.endswith(".md"):
            return "text/plain"
        if lowered.endswith(".png"):
            return "image/png"
        if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
            return "image/jpeg"
        return "application/octet-stream"


def serialize_extraction(result: ExtractionResult) -> str:
    """Canonical JSON for persistence (stable chunk order)."""
    payload = {
        "parser_version": result.parser_version,
        "chunks": [
            {
                "text": chunk.text,
                "page_number": chunk.page_number,
                "block_index": chunk.block_index,
                "bounding_box": list(chunk.bounding_box) if chunk.bounding_box else None,
            }
            for chunk in result.chunks
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
