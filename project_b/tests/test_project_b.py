"""
Pytest test suite for Project B (Data-Quality Checks).
Tests:
1. Corruption injector (all 12 problem types).
2. Declarative rules detector.
3. Statistical / ML detector.
4. LLM review detector.
5. Hybrid multi-stage pipeline.
"""

import json
from pathlib import Path
import pytest
from project_b.injector import CorruptionInjector
from project_b.detectors.declarative_rules import DeclarativeRulesDetector
from project_b.detectors.statistical_ml import StatisticalMLDetector
from project_b.detectors.llm_review import LLMReviewDetector
from project_b.hybrid_pipeline import HybridQualityPipeline

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "nyc311_sample_2023.json"


@pytest.fixture(scope="module")
def sample_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)[:500]


def test_injector_all_12_problem_types(sample_data):
    """Verify injector creates valid corrupted batches and ground truth for all 12 types."""
    injector = CorruptionInjector(seed=123)
    problems = [
        "renamed_or_dropped_column", "column_type_change", "date_format_switch",
        "lat_lon_swapped", "exact_duplicates", "near_duplicates",
        "null_spike", "closed_earlier_than_created", "zip_inconsistent_with_borough",
        "complaint_inconsistent_with_descriptor", "resolution_contradicting_status",
        "personal_data_in_free_text"
    ]
    for p in problems:
        corrupted, gt = injector.inject(sample_data, p, rate=0.06)
        assert len(corrupted) >= len(sample_data), f"Corrupted batch should be at least original size for {p}"
        assert len(gt) > 0, f"Ground truth must not be empty for {p}"
        assert all(g["problem_type"] == p for g in gt)


def test_declarative_rules_detection(sample_data):
    """Verify declarative detector catches structural and format violations."""
    injector = CorruptionInjector(seed=42)
    rules_det = DeclarativeRulesDetector()

    # Lat/Lon swapped
    corrupted, gt = injector.inject(sample_data, "lat_lon_swapped", rate=0.10)
    alerts = rules_det.detect_batch(corrupted)
    alert_types = [a["problem_type"] for a in alerts]
    assert "lat_lon_swapped" in alert_types

    # Date format switch
    corrupted, gt = injector.inject(sample_data, "date_format_switch", rate=0.10)
    alerts = rules_det.detect_batch(corrupted)
    assert any(a["problem_type"] == "date_format_switch" for a in alerts)

    # Closed date earlier than created
    corrupted, gt = injector.inject(sample_data, "closed_earlier_than_created", rate=0.10)
    alerts = rules_det.detect_batch(corrupted)
    assert any(a["problem_type"] == "closed_earlier_than_created" for a in alerts)

    # Exact duplicates
    corrupted, gt = injector.inject(sample_data, "exact_duplicates", rate=0.10)
    alerts = rules_det.detect_batch(corrupted)
    assert any(a["problem_type"] == "exact_duplicates" for a in alerts)


def test_statistical_ml_detection(sample_data):
    """Verify statistical detector catches null spikes and near-duplicates."""
    injector = CorruptionInjector(seed=42)
    stats_det = StatisticalMLDetector()

    # Null spike
    corrupted, gt = injector.inject(sample_data, "null_spike", rate=0.10)
    alerts = stats_det.detect_batch(corrupted)
    assert any(a["problem_type"] == "null_spike" for a in alerts)

    # Near duplicates
    corrupted, gt = injector.inject(sample_data, "near_duplicates", rate=0.10)
    alerts = stats_det.detect_batch(corrupted)
    assert any(a["problem_type"] == "near_duplicates" for a in alerts)


def test_llm_review_detection(sample_data):
    """Verify LLM review detects semantic contradictions and PII."""
    injector = CorruptionInjector(seed=42)
    llm_det = LLMReviewDetector()

    # Status resolution contradiction
    corrupted, gt = injector.inject(sample_data, "resolution_contradicting_status", rate=0.10)
    alerts = llm_det.detect_batch(corrupted[:50])
    assert any(a["problem_type"] == "resolution_contradicting_status" for a in alerts)

    # PII detection
    corrupted, gt = injector.inject(sample_data, "personal_data_in_free_text", rate=0.10)
    alerts = llm_det.detect_batch(corrupted[:50])
    assert any(a["problem_type"] == "personal_data_in_free_text" for a in alerts)


def test_hybrid_pipeline_end_to_end(sample_data):
    """Verify complete multi-stage hybrid pipeline execution."""
    pipeline = HybridQualityPipeline()
    injector = CorruptionInjector(seed=42)
    corrupted, gt = injector.inject(sample_data, "complaint_inconsistent_with_descriptor", rate=0.08)

    res = pipeline.run_pipeline(corrupted)
    assert res["total_rows"] == len(corrupted)
    assert res["total_alerts"] > 0
    assert "stage_breakdown" in res
    assert res["stage_breakdown"]["stage1_rules_alerts"] >= 0
    assert res["stage_breakdown"]["stage2_stats_alerts"] > 0
    assert res["cost_per_million_rows_usd"] >= 0.0
    assert res["throughput_rows_per_sec"] > 1000
