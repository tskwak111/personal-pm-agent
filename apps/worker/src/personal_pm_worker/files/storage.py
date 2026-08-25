"""Object storage port and a deterministic in-memory implementation."""

from __future__ import annotations

from typing import Protocol


class ObjectStorage(Protocol):
    async def get(self, key: str) -> bytes: ...

    async def put(self, key: str, content: bytes) -> None: ...


class InMemoryObjectStorage:
    """Process-local storage used by tests and local pipelines."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    async def get(self, key: str) -> bytes:
        if key not in self._objects:
            raise KeyError(key)
        return self._objects[key]

    async def put(self, key: str, content: bytes) -> None:
        self._objects[key] = content
