#!/usr/bin/env python3
"""Verify the Personal PM Agent development package without third-party modules."""
from __future__ import annotations

import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "00_START_HERE.md",
    "README.md",
    "AGENTS.md",
    "PACKAGE_MANIFEST.md",
    "SOURCE_SPEC_HASHES.sha256",
    "PACKAGE_SUMMARY.json",
    "MANIFEST.md",
    "MANIFEST.sha256",
    "docs/specs/2026-08-23-personal-pm-agent-design.md",
    "docs/specs/2026-08-23-personal-pm-agent-planner-normative-spec.md",
    "docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md",
    "docs/architecture/decision-precedence.md",
    "docs/architecture/domain-state-machines.md",
    "docs/architecture/engineering-standards.md",
    "docs/architecture/repository-and-module-contract.md",
    "docs/architecture/toolchain-baseline.md",
    "docs/requirements/requirements-traceability.md",
    "docs/requirements/acceptance-scenarios.md",
    "docs/quality/definition-of-done.md",
    "docs/quality/metric-gate-index.md",
    "docs/quality/verification-command-matrix.md",
    "docs/operations/security-privacy-and-runbook.md",
    "docs/status/IMPLEMENTATION_STATUS.md",
    "docs/status/DECISION_LOG.md",
    "docs/status/RISK_REGISTER.md",
    "docs/status/HANDOFF_CHECKLIST.md",
    "docs/status/VERIFICATION_EVIDENCE.md",
    "docs/templates/ADR_TEMPLATE.md",
    "docs/templates/INCIDENT_TEMPLATE.md",
    "docs/templates/RELEASE_REPORT_TEMPLATE.md",
    "docs/templates/TASK_COMPLETION_TEMPLATE.md",
    "docs/plans/00-master-implementation-roadmap.md",
    "docs/plans/01-phase-0-foundation.md",
    "docs/plans/02-phase-1-domain-core.md",
    "docs/plans/03-phase-2-planner-engine.md",
    "docs/plans/04-phase-3-persistence-api.md",
    "docs/plans/05-phase-4-intake-llm-files.md",
    "docs/plans/06-phase-5-calendar-execution.md",
    "docs/plans/07-phase-6-agent-briefing.md",
    "docs/plans/08-phase-7-web-pwa.md",
    "docs/plans/09-phase-8-evaluation-security-deployment.md",
    "prompts/README.md",
    "prompts/CODEX_MASTER_META_PROMPT.md",
    "prompts/CODEX_PHASE_PROMPTS.md",
    "prompts/CODEX_RESUME_PROMPT.md",
    "prompts/CODEX_PHASE_EXECUTION_PROMPT_TEMPLATE.md",
    "prompts/CODE_REVIEW_PROMPT.md",
    "prompts/CODEX_FINAL_AUDIT_META_PROMPT.md",
    "prompts/RELEASE_AUDIT_PROMPT.md",
    "scripts/verify_package.py",
    "scripts/build_distribution_manifest.py",
}


PLACEHOLDER_PATTERNS = (
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"implement later", re.IGNORECASE),
    re.compile(r"fill in details", re.IGNORECASE),
    re.compile(r"similar to task", re.IGNORECASE),
    re.compile(r"add appropriate error handling", re.IGNORECASE),
    re.compile(r"write tests for the above", re.IGNORECASE),
)

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".hypothesis",
        ".next",
        ".turbo",
        ".vercel",
        "dist",
        "build",
        "coverage",
        "uv-cache",
        "pnpm-store",
        ".idea",
        ".vscode",
    }
)


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_workspace_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not EXCLUDED_DIRECTORIES.intersection(path.parts)
    ]


def markdown_files() -> list[Path]:
    return sorted(path for path in iter_workspace_files() if path.suffix == ".md")


def check_required_files(errors: list[str]) -> None:
    for relative in sorted(REQUIRED_FILES):
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            fail(errors, f"missing or empty required file: {relative}")



def check_distribution_manifest(errors: list[str]) -> int:
    manifest_path = ROOT / "MANIFEST.sha256"
    lines = [line for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    listed: set[str] = set()
    for line_number, line in enumerate(lines, 1):
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError:
            fail(errors, f"invalid distribution manifest line {line_number}")
            continue
        relative = relative.strip()
        if relative in listed:
            fail(errors, f"duplicate distribution manifest path: {relative}")
            continue
        listed.add(relative)
        path = ROOT / relative
        if not path.is_file():
            fail(errors, f"distribution manifest target missing: {relative}")
        elif sha256(path) != expected:
            fail(errors, f"distribution manifest hash mismatch: {relative}")
    workspace_files = {str(path.relative_to(ROOT)) for path in iter_workspace_files()}
    untracked = sorted(set(workspace_files) - listed)
    extra = sorted(listed - workspace_files)
    if extra:
        fail(errors, f"distribution manifest coverage mismatch: extra={extra}")
    return len(listed), len(untracked)

def check_source_hashes(errors: list[str]) -> None:
    manifest = ROOT / "SOURCE_SPEC_HASHES.sha256"
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError:
            fail(errors, f"invalid source hash line {line_number}")
            continue
        path = ROOT / relative.strip()
        if not path.is_file():
            fail(errors, f"source hash target missing: {relative}")
        elif sha256(path) != expected:
            fail(errors, f"source spec hash mismatch: {relative}")


def check_markdown(errors: list[str]) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        if "\x00" in text:
            fail(errors, f"NUL byte in Markdown: {relative}")
        fence_count = sum(1 for line in text.splitlines() if re.match(r"^\s*```", line))
        if fence_count % 2:
            fail(errors, f"unbalanced fenced code block: {relative} ({fence_count})")
        for pattern in PLACEHOLDER_PATTERNS:
            match = pattern.search(text)
            if match:
                fail(errors, f"placeholder phrase {match.group(0)!r} in {relative}")
                break


def active_phase_plans() -> list[Path]:
    result: list[Path] = []
    for phase in range(9):
        matches = sorted((ROOT / "docs/plans").glob(f"{phase + 1:02d}-phase-{phase}-*.md"))
        if len(matches) != 1:
            raise RuntimeError(f"expected one plan for Phase {phase}, found {len(matches)}")
        result.extend(matches)
    return result


def check_plan_contracts(errors: list[str]) -> tuple[list[str], int]:
    ids: list[str] = []
    task_count = 0
    required_header_markers = (
        "# ",
        "For agentic workers",
        "**Goal:**",
        "**Architecture:**",
        "**Tech Stack:**",
        "**Spec:**",
        "## Global Constraints",
    )
    try:
        plans = active_phase_plans()
    except RuntimeError as exc:
        fail(errors, str(exc))
        return ids, task_count

    for phase, path in enumerate(plans):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for marker in required_header_markers:
            if marker not in text:
                fail(errors, f"plan header marker {marker!r} missing: {relative}")
        pattern = re.compile(rf"^### Task (P{phase}-T\d{{2}}): (.+)$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        if not matches:
            fail(errors, f"no stable Task IDs in {relative}")
            continue
        task_count += len(matches)
        ids.extend(match.group(1) for match in matches)
        boundaries = [match.start() for match in matches] + [len(text)]
        for index, match in enumerate(matches):
            section = text[boundaries[index] : boundaries[index + 1]]
            task_id = match.group(1)
            markers = (
                "**Files:**",
                "**Interfaces:**",
                "**Step 1:",
                "**Step 2:",
                "**Step 3:",
                "**Step 4:",
                "Commit",
                "Expected:",
            )
            for marker in markers:
                if marker not in section:
                    fail(errors, f"{task_id} missing {marker!r}")
    duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]
    if duplicate_ids:
        fail(errors, f"duplicate Task IDs: {', '.join(sorted(duplicate_ids))}")
    if task_count != 77:
        fail(errors, f"expected 77 implementation Tasks, found {task_count}")
    return ids, task_count


def check_traceability(errors: list[str], task_ids: list[str]) -> int:
    path = ROOT / "docs/requirements/requirements-traceability.md"
    text = path.read_text(encoding="utf-8")
    requirement_ids = re.findall(r"^\| (REQ-[A-Z]+-\d{3}) \|", text, re.MULTILINE)
    duplicates = [item for item, count in Counter(requirement_ids).items() if count > 1]
    if duplicates:
        fail(errors, f"duplicate requirement IDs: {', '.join(sorted(duplicates))}")
    if len(requirement_ids) < 90:
        fail(errors, f"expected at least 90 traced requirements, found {len(requirement_ids)}")
    referenced_tasks = set(re.findall(r"\bP[0-8]-T\d{2}\b", text))
    unknown = sorted(referenced_tasks - set(task_ids))
    if unknown:
        fail(errors, f"traceability references unknown Tasks: {', '.join(unknown)}")
    unreferenced = sorted(set(task_ids) - referenced_tasks)
    if unreferenced:
        fail(errors, f"Tasks missing from traceability matrix: {', '.join(unreferenced)}")
    return len(requirement_ids)


def check_scenarios(errors: list[str]) -> int:
    path = ROOT / "docs/requirements/acceptance-scenarios.md"
    text = path.read_text(encoding="utf-8")
    ids = re.findall(r"^## (SCN-\d{3}) —", text, re.MULTILINE)
    if len(ids) != 20 or len(set(ids)) != 20:
        fail(errors, f"expected 20 unique acceptance scenarios, found {len(ids)}")
    for scenario_id in ids:
        start = text.index(f"## {scenario_id}")
        next_match = re.search(r"^## SCN-\d{3}", text[start + 1 :], re.MULTILINE)
        end = start + 1 + next_match.start() if next_match else len(text)
        section = text[start:end]
        for keyword in ("Given", "When", "Then"):
            if keyword not in section:
                fail(errors, f"{scenario_id} missing Gherkin keyword {keyword}")
    return len(ids)



def check_metric_index(errors: list[str]) -> int:
    spec = (ROOT / "docs/specs/2026-08-23-personal-pm-agent-evaluation-and-pilot-plan.md").read_text(encoding="utf-8")
    index = (ROOT / "docs/quality/metric-gate-index.md").read_text(encoding="utf-8")
    pattern = r"\b(?:SAFE|PLAN|PQ|AI|EXT|OUT|UX|OPS)-\d{3}\b"
    spec_ids = set(re.findall(pattern, spec))
    index_ids = re.findall(r"^\| ((?:SAFE|PLAN|PQ|AI|EXT|OUT|UX|OPS)-\d{3}) \|", index, re.MULTILINE)
    if len(index_ids) != len(set(index_ids)):
        fail(errors, "duplicate Metric IDs in metric gate index")
    if set(index_ids) != spec_ids:
        missing = sorted(spec_ids - set(index_ids))
        extra = sorted(set(index_ids) - spec_ids)
        fail(errors, f"metric index mismatch: missing={missing}, extra={extra}")
    if len(spec_ids) != 64:
        fail(errors, f"expected 64 approved Metric IDs, found {len(spec_ids)}")
    return len(spec_ids)

def check_prompt(errors: list[str]) -> None:
    path = ROOT / "prompts/CODEX_MASTER_META_PROMPT.md"
    text = path.read_text(encoding="utf-8")
    required = (
        "superpowers:using-superpowers",
        "superpowers:using-git-worktrees",
        "superpowers:subagent-driven-development",
        "superpowers:test-driven-development",
        "superpowers:systematic-debugging",
        "superpowers:verification-before-completion",
        "P0-T01",
        "Planning Core",
        "Base and Safety",
        "transactional outbox",
        "Hard Gate",
    )
    for marker in required:
        if marker not in text:
            fail(errors, f"master prompt missing required marker: {marker}")


def check_manifest(errors: list[str]) -> None:
    path = ROOT / "PACKAGE_MANIFEST.md"
    text = path.read_text(encoding="utf-8")
    required = (
        "77개",
        "104개",
        "20개",
        "prompts/CODEX_MASTER_META_PROMPT.md",
        "docs/requirements/requirements-traceability.md",
        "docs/quality/definition-of-done.md",
        "MANIFEST.sha256",
    )
    for marker in required:
        if marker not in text:
            fail(errors, f"package manifest missing required marker: {marker}")


def check_status(errors: list[str]) -> None:
    text = (ROOT / "docs/status/IMPLEMENTATION_STATUS.md").read_text(encoding="utf-8")
    if "**현재 Phase:**" not in text or "**현재 Task:**" not in text:
        fail(errors, "implementation status must identify the current Phase and Task")
    if "P0-T01" not in text:
        fail(errors, "implementation status must reference the first Task P0-T01 in its history")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    manifest_count, untracked_count = check_distribution_manifest(errors)
    check_source_hashes(errors)
    check_markdown(errors)
    task_ids, task_count = check_plan_contracts(errors)
    requirement_count = check_traceability(errors, task_ids)
    scenario_count = check_scenarios(errors)
    metric_count = check_metric_index(errors)
    check_prompt(errors)
    check_manifest(errors)
    check_status(errors)

    if errors:
        print("Package verification FAILED", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Package verification PASSED")
    print(f"root={ROOT}")
    print(f"markdown_files={len(markdown_files())}")
    print(f"implementation_tasks={task_count}")
    print(f"traced_requirements={requirement_count}")
    print(f"acceptance_scenarios={scenario_count}")
    print(f"approved_metrics={metric_count}")
    print("source_spec_hashes=3/3")
    print(f"manifest_files={manifest_count}")
    print(f"workspace_files_not_in_manifest={untracked_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
