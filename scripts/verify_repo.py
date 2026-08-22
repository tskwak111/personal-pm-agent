#!/usr/bin/env python3
"""Verify repository-level contracts: pinned toolchains, lockfiles and infra files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ARTIFACTS = (
    ".python-version",
    ".node-version",
    "package.json",
    "pnpm-workspace.yaml",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "uv.lock",
    "compose.yaml",
    "Makefile",
    ".env.example",
)

REQUIRED_WORKSPACE_MEMBERS = (
    ("packages/planner", "personal-pm-planner"),
    ("apps/api", "personal-pm-api"),
    ("apps/worker", "personal-pm-worker"),
)


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_ARTIFACTS:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty artifact: {relative}")

    root_pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for directory, package in REQUIRED_WORKSPACE_MEMBERS:
        member_pyproject = ROOT / directory / "pyproject.toml"
        if not member_pyproject.is_file():
            errors.append(f"missing workspace member pyproject: {directory}")
            continue
        if f'"{package}"' not in root_pyproject:
            errors.append(f"workspace member not registered at root: {package}")

    lockfiles = {
        "uv.lock": "personal-pm-planner",
        "pnpm-lock.yaml": "apps/web",
    }
    for lockfile, needle in lockfiles.items():
        text = (ROOT / lockfile).read_text(encoding="utf-8")
        if needle not in text:
            errors.append(f"{lockfile} does not contain {needle}")

    if errors:
        print("Repository verification FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository verification PASSED")
    print(f"artifacts={len(REQUIRED_ARTIFACTS)}")
    print(f"workspace_members={len(REQUIRED_WORKSPACE_MEMBERS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
