from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest_asyncio


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]

    async def put(self, key: str, content: bytes) -> None:
        self.objects[key] = content


@pytest_asyncio.fixture
async def pipeline_env() -> AsyncIterator[dict[str, Any]]:
    from personal_pm_worker.files.parsers import ExtractionChunk, ExtractionResult
    from personal_pm_worker.files.pipeline import ExtractionPipeline
    from personal_pm_worker.files.storage import InMemoryObjectStorage

    storage = InMemoryObjectStorage()
    calls: list[tuple[bytes, str]] = []

    class CountingParser:
        parser_call_count = 0

        async def parse(self, content: bytes, content_type: str) -> ExtractionResult:
            type(self).parser_call_count += 1
            calls.append((content, content_type))
            return ExtractionResult(
                chunks=(
                    ExtractionChunk(
                        text="page one text", page_number=1, block_index=0, bounding_box=None
                    ),
                    ExtractionChunk(
                        text="page two text", page_number=2, block_index=0, bounding_box=None
                    ),
                ),
                parser_version="pdf-v1",
            )

    parser = CountingParser()
    pipeline = ExtractionPipeline(storage=storage, parser=parser)

    stored_key = "workspaces/ws-1/source-artifacts/a1/sample.pdf"
    await storage.put(stored_key, b"%PDF-fake")

    yield {
        "pipeline": pipeline,
        "storage": storage,
        "key": stored_key,
        "parser": parser,
    }


async def test_same_source_and_parser_version_reuses_extraction(
    pipeline_env: dict[str, Any],
) -> None:
    pipeline = pipeline_env["pipeline"]
    first = await pipeline.extract(pipeline_env["key"], parser_version="pdf-v1")
    second = await pipeline.extract(pipeline_env["key"], parser_version="pdf-v1")
    assert second.id == first.id
    assert second.result.chunks == first.result.chunks
    # plan contract: same source + same parser version must parse only once
    assert pipeline_env["parser"].parser_call_count == 1


async def test_extraction_preserves_page_source_locations(
    pipeline_env: dict[str, Any],
) -> None:
    pipeline = pipeline_env["pipeline"]
    record = await pipeline.extract(pipeline_env["key"], parser_version="pdf-v1")
    assert all(chunk.page_number is not None for chunk in record.result.chunks)


async def test_different_parser_version_creates_new_extraction(
    pipeline_env: dict[str, Any],
) -> None:
    pipeline = pipeline_env["pipeline"]
    first = await pipeline.extract(pipeline_env["key"], parser_version="pdf-v1")
    second = await pipeline.extract(pipeline_env["key"], parser_version="pdf-v2")
    assert second.id != first.id
