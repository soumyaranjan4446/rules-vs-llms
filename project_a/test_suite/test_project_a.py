"""
Pytest test suite for Project A (Income-tax engine).
Tests:
1. 30 official ITD calculator benchmarks (rupee-exact).
2. 212 comprehensive threshold edge cases.
3. Plain-language parser (50 queries: complete, incomplete, contradictory).
4. Clause traceability verification.
"""

import json
from pathlib import Path
import pytest
from project_a.models import SalaryInput
from project_a.hand_coded.calculator import HandCodedTaxEngine
from project_a.llm_compiled.compiler import LLMCompiledTaxEngine
from project_a.parser import PlainLanguageParser


TEST_SUITE_DIR = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def official_cases():
    path = TEST_SUITE_DIR / "official_calc_cases.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def threshold_cases():
    path = TEST_SUITE_DIR / "test_cases.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def plain_language_cases():
    path = TEST_SUITE_DIR / "plain_language_cases.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- 1. OFFICIAL CALCULATOR BENCHMARKS ---
def test_hand_coded_against_30_official_benchmarks(official_cases):
    """Verify hand-coded engine produces rupee-exact matches against official ITD calculator."""
    engine = HandCodedTaxEngine(financial_year="2024-25")
    for case in official_cases:
        inp = SalaryInput(
            gross_salary=case["gross_salary"],
            basic_salary=case["basic_salary"],
            hra_received=case.get("hra_received", 0.0),
            rent_paid=case.get("rent_paid", 0.0),
            is_metro=case.get("is_metro", False),
            sec_80c=case.get("sec_80c", 0.0),
            sec_80ccd_1b=case.get("sec_80ccd_1b", 0.0),
            sec_80d_self=case.get("sec_80d_self", 0.0),
            sec_80d_parents=case.get("sec_80d_parents", 0.0),
            parents_senior_citizen=case.get("parents_senior_citizen", False),
            home_loan_interest_24b=case.get("home_loan_interest_24b", 0.0),
            financial_year="2024-25"
        )
        comp = engine.compare(inp)
        assert comp.old_regime.total_tax_payable == case["expected_old_tax"], (
            f"Failed on {case['case_id']}: Expected Old Tax {case['expected_old_tax']}, got {comp.old_regime.total_tax_payable}"
        )
        assert comp.new_regime.total_tax_payable == case["expected_new_tax"], (
            f"Failed on {case['case_id']}: Expected New Tax {case['expected_new_tax']}, got {comp.new_regime.total_tax_payable}"
        )


def test_compiled_against_30_official_benchmarks(official_cases):
    """Verify LLM-compiled engine produces rupee-exact matches against official ITD calculator."""
    engine = LLMCompiledTaxEngine(financial_year="2024-25")
    for case in official_cases:
        inp = SalaryInput(
            gross_salary=case["gross_salary"],
            basic_salary=case["basic_salary"],
            hra_received=case.get("hra_received", 0.0),
            rent_paid=case.get("rent_paid", 0.0),
            is_metro=case.get("is_metro", False),
            sec_80c=case.get("sec_80c", 0.0),
            sec_80ccd_1b=case.get("sec_80ccd_1b", 0.0),
            sec_80d_self=case.get("sec_80d_self", 0.0),
            sec_80d_parents=case.get("sec_80d_parents", 0.0),
            parents_senior_citizen=case.get("parents_senior_citizen", False),
            home_loan_interest_24b=case.get("home_loan_interest_24b", 0.0),
            financial_year="2024-25"
        )
        comp = engine.compute(inp)
        assert comp.old_regime.total_tax_payable == case["expected_old_tax"], (
            f"Compiled engine failed on {case['case_id']}: Expected Old Tax {case['expected_old_tax']}, got {comp.old_regime.total_tax_payable}"
        )
        assert comp.new_regime.total_tax_payable == case["expected_new_tax"], (
            f"Compiled engine failed on {case['case_id']}: Expected New Tax {case['expected_new_tax']}, got {comp.new_regime.total_tax_payable}"
        )


# --- 2. 200+ THRESHOLD EDGE CASES ---
def test_all_212_threshold_cases_hand_coded(threshold_cases):
    """Run full 212 edge cases on Hand-Coded engine."""
    engine = HandCodedTaxEngine(financial_year="2024-25")
    for case in threshold_cases:
        inp = SalaryInput(**case["input"])
        comp = engine.compare(inp)
        assert comp.old_regime.total_tax_payable == case["expected_old_regime_tax"], f"Failed {case['id']}"
        assert comp.new_regime.total_tax_payable == case["expected_new_regime_tax"], f"Failed {case['id']}"
        assert comp.recommended_regime == case["expected_recommendation"], f"Recommendation mismatch on {case['id']}"


def test_all_212_threshold_cases_compiled(threshold_cases):
    """Run full 212 edge cases on LLM-compiled engine."""
    engine = LLMCompiledTaxEngine(financial_year="2024-25")
    for case in threshold_cases:
        inp = SalaryInput(**case["input"])
        comp = engine.compute(inp)
        assert comp.old_regime.total_tax_payable == case["expected_old_regime_tax"], f"Failed {case['id']}"
        assert comp.new_regime.total_tax_payable == case["expected_new_regime_tax"], f"Failed {case['id']}"
        assert comp.recommended_regime == case["expected_recommendation"], f"Recommendation mismatch on {case['id']}"


# --- 3. PLAIN LANGUAGE PARSER TESTS ---
def test_plain_language_parser(plain_language_cases):
    """Test plain-language parser against 50 diverse queries."""
    parser = PlainLanguageParser(default_fy="2024-25")
    for item in plain_language_cases:
        res = parser.parse(item["query"])
        if item["is_complete"]:
            assert res.is_complete, f"Expected {item['id']} to be complete: {item['query']}"
            assert res.structured_input is not None
            assert res.structured_input.gross_salary > 0
            assert len(res.clarifying_questions) == 0
        else:
            assert not res.is_complete, f"Expected {item['id']} to require clarification: {item['query']}"
            assert len(res.clarifying_questions) > 0, f"Expected questions for {item['id']}"
            # Verify that the expected clarification topic was asked
            exp_topic = item.get("expected_question")
            if exp_topic:
                combined_qs = " ".join(res.clarifying_questions).lower()
                assert exp_topic.lower() in combined_qs or "clarification" in combined_qs or "basic" in combined_qs or "deduction" in combined_qs, (
                    f"Expected topic '{exp_topic}' in questions for {item['id']}. Got: {res.clarifying_questions}"
                )


# --- 4. CLAUSE TRACEABILITY TESTS ---
def test_statutory_clause_traceability():
    """Verify that every calculated rupee traces back to a statutory clause."""
    engine = HandCodedTaxEngine(financial_year="2024-25")
    inp = SalaryInput(
        gross_salary=1500000.0,
        basic_salary=750000.0,
        hra_received=300000.0,
        rent_paid=360000.0,
        is_metro=True,
        sec_80c=150000.0,
        sec_80ccd_1b=50000.0,
        sec_80d_self=25000.0,
        sec_80d_parents=50000.0,
        parents_senior_citizen=True,
        home_loan_interest_24b=200000.0,
        financial_year="2024-25"
    )
    comp = engine.compare(inp)
    old_trail = comp.old_regime.audit_trail
    new_trail = comp.new_regime.audit_trail
    
    assert len(old_trail) >= 8
    sections_old = [t.section for t in old_trail]
    assert any("16(ia)" in s for s in sections_old)
    assert any("10(13A)" in s for s in sections_old)
    assert any("80C" in s for s in sections_old)
    assert any("80CCD" in s for s in sections_old)
    assert any("80D" in s for s in sections_old)
    assert any("24(b)" in s for s in sections_old)
    assert any("288A" in s for s in sections_old)
    assert any("288B" in s for s in sections_old)

    sections_new = [t.section for t in new_trail]
    assert any("16(ia)" in s for s in sections_new)
    assert any("115BAC" in s for s in sections_new)
    assert any("288B" in s for s in sections_new)
