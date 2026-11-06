"""
Compiled Tax Rules for FY 2025-26 (AY 2026-27).
Generated once from Finance Act 2025 statutory amendments by LLM Compiler and human-reviewed.
Reflects revised New Regime slabs up to 24L+ and 12L Section 87A rebate limit.
"""

from typing import Dict, Any, List
from project_a.models import SalaryInput, TaxBreakdown, RegimeComparison, ClauseTrace


def _round_10(v: float) -> float:
    return float(round(v / 10.0) * 10) if v % 10 != 5 else float(int(v // 10 + 1) * 10)


def compute_compiled_fy25_26(inp: SalaryInput) -> RegimeComparison:
    """Compiled execution of FY 2025-26 tax provisions."""
    traces_old = []
    traces_new = []

    # Old Regime is unchanged from FY 2024-25
    from project_a.llm_compiled.compiled_fy24_25 import compute_compiled_fy24_25
    res_base = compute_compiled_fy24_25(inp)
    old_breakdown = res_base.old_regime
    old_breakdown.financial_year = "2025-26"

    # --- REVISED NEW REGIME (FY 2025-26) ---
    std_ded_new = min(75000.0, inp.gross_salary)
    traces_new.append(ClauseTrace(
        section="Sec 16(ia) read with Sec 115BAC",
        description="Standard deduction under New Regime (FY 2025-26)",
        amount=std_ded_new,
        legal_rule="Flat Rs. 75,000"
    ))

    ti_new = _round_10(max(0.0, inp.gross_salary - std_ded_new))

    # FY 2025-26 Slabs:
    # 0-4L: 0%, 4-8L: 5%, 8-12L: 10%, 12-16L: 15%, 16-20L: 20%, 20-24L: 25%, >24L: 30%
    base_tax_new = 0.0
    r = ti_new
    if r > 2400000.0:
        base_tax_new += (r - 2400000.0) * 0.30
        r = 2400000.0
    if r > 2000000.0:
        base_tax_new += (r - 2000000.0) * 0.25
        r = 2000000.0
    if r > 1600000.0:
        base_tax_new += (r - 1600000.0) * 0.20
        r = 1600000.0
    if r > 1200000.0:
        base_tax_new += (r - 1200000.0) * 0.15
        r = 1200000.0
    if r > 800000.0:
        base_tax_new += (r - 800000.0) * 0.10
        r = 800000.0
    if r > 400000.0:
        base_tax_new += (r - 400000.0) * 0.05

    rebate_87a_new = 0.0
    marginal_relief_87a_new = 0.0
    if ti_new <= 1200000.0:
        rebate_87a_new = base_tax_new
        tax_after_rebate_new = 0.0
    else:
        excess = ti_new - 1200000.0
        if base_tax_new > excess:
            marginal_relief_87a_new = base_tax_new - excess
            tax_after_rebate_new = excess
        else:
            tax_after_rebate_new = base_tax_new

    # Surcharge (New regime capped at 25%)
    surcharge_new = _calc_surcharge_fy25_26(ti_new, tax_after_rebate_new)
    tax_after_sur_new = tax_after_rebate_new + surcharge_new
    cess_new = tax_after_sur_new * 0.04
    tot_tax_new = _round_10(tax_after_sur_new + cess_new)

    new_breakdown = TaxBreakdown(
        regime="new",
        financial_year="2025-26",
        gross_salary=inp.gross_salary,
        standard_deduction=std_ded_new,
        hra_exemption=0.0,
        sec_24b_loss=0.0,
        sec_80c_allowed=0.0,
        sec_80ccd_1b_allowed=0.0,
        sec_80d_allowed=0.0,
        total_deductions=std_ded_new,
        gross_total_income=ti_new,
        net_taxable_income=ti_new,
        base_tax=base_tax_new,
        rebate_87a=rebate_87a_new,
        marginal_relief_87a=marginal_relief_87a_new,
        tax_after_rebate=tax_after_rebate_new,
        surcharge=surcharge_new,
        surcharge_marginal_relief=0.0,
        tax_after_surcharge=tax_after_sur_new,
        cess=cess_new,
        total_tax_payable=tot_tax_new,
        audit_trail=traces_new
    )

    diff = abs(old_breakdown.total_tax_payable - tot_tax_new)
    if old_breakdown.total_tax_payable < tot_tax_new:
        rec = "old"
        reason = f"Old regime saves Rs. {diff:,.0f}."
    elif tot_tax_new < old_breakdown.total_tax_payable:
        rec = "new"
        reason = f"New regime saves Rs. {diff:,.0f} due to expanded FY 2025-26 slabs and 12L rebate."
    else:
        rec = "either"
        reason = f"Both regimes equal at Rs. {tot_tax_new:,.0f}."

    return RegimeComparison(
        old_regime=old_breakdown,
        new_regime=new_breakdown,
        recommended_regime=rec,
        tax_difference=diff,
        recommendation_reason=reason,
        is_exact_match=True
    )


def _calc_surcharge_fy25_26(ti: float, tax: float) -> float:
    if ti <= 5000000.0 or tax <= 0:
        return 0.0
    if ti <= 10000000.0:
        rate = 0.10
        prev_limit = 5000000.0
        prev_rate = 0.0
    elif ti <= 20000000.0:
        rate = 0.15
        prev_limit = 10000000.0
        prev_rate = 0.10
    elif ti <= 50000000.0:
        rate = 0.25
        prev_limit = 20000000.0
        prev_rate = 0.15
    else:
        rate = 0.25
        prev_limit = 50000000.0
        prev_rate = 0.25

    nom = tax * rate
    t_prev = _slab_tax_fy25_26(prev_limit)
    max_tot = (t_prev * (1.0 + prev_rate)) + (ti - prev_limit)
    if tax + nom > max_tot:
        return max(0.0, max_tot - tax)
    return nom


def _slab_tax_fy25_26(inc: float) -> float:
    r = inc
    tax = 0.0
    if r > 2400000.0:
        tax += (r - 2400000.0) * 0.30
        r = 2400000.0
    if r > 2000000.0:
        tax += (r - 2000000.0) * 0.25
        r = 2000000.0
    if r > 1600000.0:
        tax += (r - 1600000.0) * 0.20
        r = 1600000.0
    if r > 1200000.0:
        tax += (r - 1200000.0) * 0.15
        r = 1200000.0
    if r > 800000.0:
        tax += (r - 800000.0) * 0.10
        r = 800000.0
    if r > 400000.0:
        tax += (r - 400000.0) * 0.05
    return tax
