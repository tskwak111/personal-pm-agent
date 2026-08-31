"""Upload content scanning: magic bytes beat declared content types."""

from __future__ import annotations

from dataclasses import dataclass

EXECUTABLE_MAGIC = (
    b"MZ",
    b"\x7fELF",
    b"\xca\xfe\xba\xbe",
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
)
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAGIC_BY_TYPE = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}
SUPPORTED_UPLOAD_TYPES = frozenset((*MAGIC_BY_TYPE, "text/plain"))


@dataclass(frozen=True, slots=True)
class ScanVerdict:
    allowed: bool
    reason: str | None = None
    code: str | None = None
    status_code: int = 200


def _reject(reason: str, *, mismatch: bool = False) -> ScanVerdict:
    return ScanVerdict(
        allowed=False,
        reason=reason,
        code="UPLOAD_TYPE_MISMATCH" if mismatch else "UPLOAD_REJECTED",
        status_code=415 if mismatch else 422,
    )


def scan_upload(content: bytes, *, declared_type: str) -> ScanVerdict:
    media_type = declared_type.partition(";")[0].strip().lower()
    if not content:
        return _reject("empty upload")
    if len(content) > MAX_UPLOAD_BYTES:
        return _reject("upload exceeds size limit")
    for magic in EXECUTABLE_MAGIC:
        if content.startswith(magic):
            return _reject("executable content detected")
    if media_type not in SUPPORTED_UPLOAD_TYPES:
        return _reject("unsupported declared content type", mismatch=True)

    detected_type = next(
        (kind for kind, magic in MAGIC_BY_TYPE.items() if content.startswith(magic)), None
    )
    if media_type == "text/plain":
        if detected_type is not None:
            return _reject("binary magic does not match text/plain", mismatch=True)
        if b"\x00" in content:
            return _reject("binary payload in text upload")
        try:
            content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return _reject("text upload is not valid UTF-8")
    elif detected_type != media_type:
        return _reject("declared type does not match file magic", mismatch=True)
    return ScanVerdict(allowed=True)


__all__ = [
    "MAX_UPLOAD_BYTES",
    "SUPPORTED_UPLOAD_TYPES",
    "ScanVerdict",
    "scan_upload",
]
