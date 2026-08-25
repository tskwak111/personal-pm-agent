"""Typed LLM gateway errors."""

from __future__ import annotations


class PromptNotFoundError(Exception):
    def __init__(self, prompt_version: str) -> None:
        super().__init__(f"unknown prompt version: {prompt_version}")


class StructuredLLMError(Exception):
    """Both the original response and the single repair failed validation."""
