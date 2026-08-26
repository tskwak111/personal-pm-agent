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


def test_precision_recall_uses_fixed_gold_denominator() -> None:
    result = compute_precision_recall(true_positive=95, false_positive=1, false_negative=5)
    assert result.precision == pytest.approx(95 / 96)
    assert result.recall == pytest.approx(95 / 100)


@pytest.fixture
def sample_stage_b_counts() -> dict[str, float]:
    return {
        "AI-001": 0.99,
        "AI-002": 1.00,
        "AI-010": 0.995,
        "AI-011": 0.96,
        "AI-012": 1.00,
        "AI-013": 0.985,
        "PQ-RISK-MACRO-F1": 0.92,
        "PQ-P0-P1-RECALL": 0.99,
        "PQ-AUTH-ACCURACY": 1.00,
    }


def test_required_metric_below_threshold_fails_stage(
    sample_stage_b_counts: dict[str, float],
) -> None:
    sample_stage_b_counts["AI-010"] = 0.98
    assert build_stage_b_report(sample_stage_b_counts).overall == "FAIL"


def test_all_thresholds_met_passes_stage(
    sample_stage_b_counts: dict[str, float],
) -> None:
    assert build_stage_b_report(sample_stage_b_counts).overall == "PASS"
