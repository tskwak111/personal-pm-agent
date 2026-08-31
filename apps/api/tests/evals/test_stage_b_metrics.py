from __future__ import annotations

import importlib.util
import sys
from pathlib import Path as _Path
from typing import Any

import pytest

_REPO_ROOT_B = _Path(__file__).resolve().parents[4]
_spec_b = importlib.util.spec_from_file_location(
    "run_stage_b", _REPO_ROOT_B / "scripts" / "run_stage_b.py"
)
assert _spec_b is not None and _spec_b.loader is not None
_mod_b: Any = importlib.util.module_from_spec(_spec_b)
sys.modules["run_stage_b"] = _mod_b
_spec_b.loader.exec_module(_mod_b)

build_stage_b_report = _mod_b.build_stage_b_report
compute_precision_recall = _mod_b.compute_precision_recall
count_jsonl_records = _mod_b.count_jsonl_records
DatasetError = _mod_b.DatasetError


def test_precision_recall_uses_fixed_gold_denominator() -> None:
    result = compute_precision_recall(true_positive=95, false_positive=1, false_negative=5)
    assert result.precision == pytest.approx(95 / 96)
    assert result.recall == pytest.approx(95 / 100)


@pytest.fixture
def sample_stage_b_counts() -> dict[str, float]:
    return {
        "AI-001": 0.99,
        "AI-002": 1.00,
        "AI-003": 1.00,
        "AI-004": 0.00,
        "AI-005": 0.00,
        "AI-010": 0.995,
        "AI-011": 0.96,
        "AI-012": 1.00,
        "AI-013": 0.985,
        "AI-014": 0.00,
        "AI-015": 1.00,
        "PQ-RISK-MACRO-F1": 0.92,
        "PQ-P0-P1-RECALL": 0.99,
        "PQ-AUTH-ACCURACY": 1.00,
        "PQ-UNREALISTIC-PLANS": 0.00,
    }


def test_required_metric_below_threshold_fails_stage(
    sample_stage_b_counts: dict[str, float],
) -> None:
    sample_stage_b_counts["AI-010"] = 0.98
    assert (
        build_stage_b_report(sample_stage_b_counts, golden_count=200, expert_count=150).overall
        == "FAIL"
    )


def test_all_thresholds_met_passes_stage(
    sample_stage_b_counts: dict[str, float],
) -> None:
    assert (
        build_stage_b_report(sample_stage_b_counts, golden_count=200, expert_count=150).overall
        == "PASS"
    )


def test_missing_required_metric_is_not_coerced_to_zero(
    sample_stage_b_counts: dict[str, float],
) -> None:
    del sample_stage_b_counts["AI-010"]

    report = build_stage_b_report(sample_stage_b_counts, golden_count=200, expert_count=150)

    assert report.overall == "FAIL"
    assert report.metrics["AI-010"]["status"] == "MISSING"


def test_small_private_corpus_is_blocked(
    sample_stage_b_counts: dict[str, float],
) -> None:
    report = build_stage_b_report(sample_stage_b_counts, golden_count=3, expert_count=2)

    assert report.overall == "BLOCKED_EXTERNAL"
    assert report.denominators == {"golden_sources": 3, "expert_scenarios": 2}


def test_duplicate_dataset_ids_are_rejected(tmp_path: _Path) -> None:
    (tmp_path / "cases.jsonl").write_text(
        '{"case_id":"same"}\n{"case_id":"same"}\n', encoding="utf-8"
    )

    with pytest.raises(DatasetError, match="duplicate dataset ID"):
        count_jsonl_records(tmp_path, id_fields=("case_id",))
