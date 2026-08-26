"""Upload content scanning: magic bytes beat declared content types."""

from __future__ import annotations

from dataclasses import dataclass

EXECUTABLE_MAGIC = (b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe")


@dataclass(frozen=True, slots=True)
class ScanVerdict:
    allowed: bool
    reason: str | None = None


def scan_upload(content: bytes, *, declared_type: str) -> ScanVerdict:
    for magic in EXECUTABLE_MAGIC:
        if content.startswith(magic):
            return ScanVerdict(allowed=False, reason="executable content detected")
    if declared_type == "text/plain" and b"\x00" in content:
        return ScanVerdict(allowed=False, reason="binary payload in text upload")
    return ScanVerdict(allowed=True)


__all__ = ["ScanVerdict", "scan_upload"]
