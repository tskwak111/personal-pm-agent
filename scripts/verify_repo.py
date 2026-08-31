#!/usr/bin/env python3
"""Verify repository-level contracts: pinned toolchains, lockfiles and infra files."""

from __future__ import annotations

import re
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

_LOCAL_REFERENCE = re.compile(
    r"(?:\.\./)+[A-Za-z0-9_./-]+|"
    r"/?(?:apps|packages|tests|scripts|docs|evals|reports|pilot|infra|artifacts|prompts|\.github)"
    r"/[A-Za-z0-9_./*?-]+(?:::[A-Za-z_][A-Za-z0-9_]*)*"
)


def verify_traceability(document: Path, *, repo_root: Path) -> list[str]:
    root = repo_root.resolve()
    errors: list[str] = []
    for line in document.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Requirement ID", "---"} or set(cells[0]) == {"-"}:
            continue
        requirement = cells[0]
        row = " | ".join(cells)
        if "BLOCKED_EXTERNAL" in row or "Not Implemented" in row:
            continue
        references = _LOCAL_REFERENCE.findall(cells[-1])
        if "Complete" in cells and not references:
            errors.append(f"{requirement}: Complete has no local evidence")
            continue
        for reference in references:
            path_text, *nodes = reference.split("::")
            candidate = Path(path_text)
            resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
            if not resolved.is_relative_to(root):
                errors.append(f"{requirement}: evidence path escapes repository: {path_text}")
                continue
            if "*" in path_text:
                if not list(root.glob(path_text)):
                    errors.append(f"{requirement}: missing evidence path {path_text}")
                continue
            if not resolved.exists():
                errors.append(f"{requirement}: missing evidence path {path_text}")
                continue
            if nodes:
                if not resolved.is_file():
                    errors.append(f"{requirement}: pytest node path is not a file {path_text}")
                    continue
                source = resolved.read_text(encoding="utf-8")
                for node in nodes:
                    if re.search(rf"\b(?:def|class)\s+{re.escape(node)}\b", source) is None:
                        errors.append(f"{requirement}: missing pytest node {reference}")
                        break
    return errors


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

    errors.extend(
        verify_traceability(
            ROOT / "docs/requirements/requirements-traceability.md",
            repo_root=ROOT,
        )
    )

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
