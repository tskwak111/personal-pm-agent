from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "run_intake_eval", _REPO_ROOT / "scripts" / "run_intake_eval.py"
)
assert _spec is not None and _spec.loader is not None
_mod: Any = importlib.util.module_from_spec(_spec)
sys.modules["run_intake_eval"] = _mod
_spec.loader.exec_module(_mod)

evaluate_cases = _mod.evaluate_cases
load_cases = _mod.load_cases


def _sample_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "case-001",
            "source_text": "CS101 보고서는 2026-09-01까지 제출",
            "expected": {
                "kind": "HARD_DEADLINE",
                "title": "CS101 보고서 제출",
                "due_date": "2026-09-01",
            },
            "llm_raw": (
                '{"kind": "HARD_DEADLINE", "title": "CS101 보고서 제출", "due_date": "2026-09-01"}'
            ),
            "repair_raw": None,
        },
        {
            "case_id": "case-002",
            "source_text": "팀 회의 다음 주",
            "expected": {
                "kind": "FIXED_EVENT",
                "title": "팀 회의",
                "due_date": None,
            },
            # first pass invalid (missing kind), repair succeeds
            "llm_raw": '{"title": "팀 회의"}',
            "repair_raw": '{"kind": "FIXED_EVENT", "title": "팀 회의", "due_date": null}',
        },
        {
            "case_id": "case-003",
            "source_text": "메모: 라이브러리 반납",
            "expected": {"kind": "REFERENCE_NOTE", "title": "라이브러리 반납", "due_date": None},
            # both passes invalid → failed case still counted in denominators
            "llm_raw": "{broken json",
            "repair_raw": '{"wrong": 1}',
        },
    ]


def test_eval_runner_counts_failed_cases_in_denominator() -> None:
    cases = _sample_cases()
    report = evaluate_cases(cases)
    assert report.metrics["AI-001"].denominator == len(cases)


def test_report_separates_first_pass_and_repaired_success() -> None:
    cases = _sample_cases()
    report = evaluate_cases(cases)
    # AI-001: first-pass success = case-001 only
    assert report.metrics["AI-001"].numerator == 1
    # AI-002: first pass + repaired success = case-001 + case-002
    assert report.metrics["AI-002"].numerator == 2
    assert report.metrics["AI-002"].numerator >= report.metrics["AI-001"].numerator


def test_load_cases_reads_jsonl_fixture() -> None:
    fixture = (
        Path(__file__).resolve().parents[4] / "evals" / "golden" / "fixtures" / "sample-cases.jsonl"
    )
    cases = load_cases(fixture)
    assert len(cases) >= 1
