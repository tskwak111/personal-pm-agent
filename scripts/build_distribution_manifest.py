#!/usr/bin/env python3
"""Regenerate MANIFEST.md and MANIFEST.sha256 for the development package."""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_MD = ROOT / "MANIFEST.md"
MANIFEST_SHA = ROOT / "MANIFEST.sha256"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(*, include_manifest_md: bool) -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path == MANIFEST_SHA:
            continue
        if not include_manifest_md and path == MANIFEST_MD:
            continue
        result.append(path)
    return sorted(result, key=lambda item: str(item.relative_to(ROOT)))


def build_markdown() -> str:
    files = included_files(include_manifest_md=False)
    top_level = Counter(path.relative_to(ROOT).parts[0] for path in files)
    inventory = "\n".join(
        f"| `{path.relative_to(ROOT)}` | {path.stat().st_size} | `{sha256(path)}` |"
        for path in files
    )
    top_rows = "\n".join(f"| `{name}` | {count} |" for name, count in sorted(top_level.items()))
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    return f"""# Development Package Manifest

- **Package:** Personal PM Agent Final Development Package
- **Version:** 1.0.0
- **Manifest regenerated:** {generated}
- **Product implementation status:** not started; this manifest verifies development-package artifacts only

## Package metrics

- Approved source specifications: 3
- Implementation Phases: 9
- TDD implementation Tasks: 77
- Traced requirements: 104
- Acceptance scenarios: 20
- Approved evaluation Metric IDs: 64

## Top-level inventory before manifest files

| Area | Files |
|---|---:|
{top_rows}

## File inventory before manifest files

| Path | Bytes | SHA-256 |
|---|---:|---|
{inventory}

## Verification

Run from the package root:

```bash
python3 scripts/verify_package.py

# Optional per-file checksum verification
sha256sum -c MANIFEST.sha256        # Linux
shasum -a 256 -c MANIFEST.sha256   # macOS
```

`MANIFEST.sha256` includes `MANIFEST.md` and every package file except itself, Python bytecode and `__pycache__` artifacts.
"""


def main() -> None:
    MANIFEST_MD.write_text(build_markdown(), encoding="utf-8")
    checksum_lines = [
        f"{sha256(path)}  {path.relative_to(ROOT)}"
        for path in included_files(include_manifest_md=True)
    ]
    MANIFEST_SHA.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST_MD.relative_to(ROOT)}")
    print(f"wrote {MANIFEST_SHA.relative_to(ROOT)} with {len(checksum_lines)} entries")


if __name__ == "__main__":
    main()
