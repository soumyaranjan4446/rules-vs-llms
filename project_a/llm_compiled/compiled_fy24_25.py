"""
Compiled Tax Rules for FY 2024-25 (AY 2025-26).
Generated once from official statutory provisions by LLM Compiler and human-reviewed.
Runs deterministically in production with zero runtime LLM dependency.
"""

from typing import Dict, Any, List
from project_a.models import SalaryInput, TaxBreakdown, RegimeComparison, ClauseTrace


def _round_10(v: float) -> float:
    return float(round(v / 10.0) * 10) if v % 10 != 5 else float(int(v // 10 + 1) * 10)


def compute_compiled_fy24_25(inp: SalaryInput) -> RegimeComparison:
    """Compiled execution of FY 2024-25 tax provisions."""
    traces_old = []
    traces_new = []

    # --- OLD REGIME CALCULATION ---
    # 1. Standard deduction (Sec 16(ia))
    std_ded_old = min(50000.0, inp.gross_salary)
    traces_old.append(ClauseTrace(
        section="Sec 16(ia)",
        description="Standard Deduction",
        amount=std_ded_old,
        legal_rule="Min(Rs. 50,000, Gross Salary)"
    ))

    # 2. HRA Exemption (Sec 10(13A) + Rule 2A)
    hra_ex = 0.0
    if inp.hra_received > 0 and inp.rent_paid > 0 and inp.basic_salary > 0:
        c1 = inp.hra_received
        c2 = max(0.0, inp.rent_paid - (0.10 * inp.basic_salary))
        c3 = (0.50 if inp.is_metro else 0.40) * inp.basic_salary
        hra_ex = min(c1, c2, c3)
    traces_old.append(ClauseTrace(
        section="Sec 10(13A)",
        description="HRA Exemption",
        amount=hra_ex,
        legal_rule="Least of: actual HRA, rent - 10% basic, metro/non-metro cap"
    ))

    # 3. Sec 24(b) Home loan interest
    sec_24b = min(200000.0, inp.home_loan_interest_24b)
    traces_old.append(ClauseTrace(
        section="Sec 24(b)",
        description="Self-occupied house loan interest",
        amount=sec_24b,
        legal_rule="Capped at Rs. 2,00,000"
    ))

    # 4. Chapter VI-A Deductions
    sec_80c = min(150000.0, inp.sec_80c)
    sec_80ccd_1b = min(50000.0, inp.sec_80ccd_1b)
    lim_self = 50000.0 if inp.self_senior_citizen else 25000.0
    lim_par = 50000.0 if inp.parents_senior_citizen else 25000.0
    sec_80d = min(lim_self, inp.sec_80d_self) + min(lim_par, inp.sec_80d_parents)

    total_ded_old = std_ded_old + hra_ex + sec_24b + sec_80c + sec_80ccd_1b + sec_80d
    gti_old = max(0.0, inp.gross_salary - std_ded_old - hra_ex - sec_24b)
    ti_old = _round_10(max(0.0, inp.gross_salary - total_ded_old))

    # Old Regime Tax Slabs
    base_tax_old = 0.0
    first_slab_old = 300000.0 if inp.self_senior_citizen else 250000.0
    r = ti_old
    if r > 1000000.0:
        base_tax_old += (r - 1000000.0) * 0.30
        r = 1000000.0
    if r > 500000.0:
        base_tax_old += (r - 500000.0) * 0.20
        r = 500000.0
    if r > first_slab_old:
        base_tax_old += (r - first_slab_old) * 0.05

    # Section 87A Rebate (Old)
    rebate_87a_old = min(base_tax_old, 12500.0) if ti_old <= 500000.0 else 0.0
    tax_after_rebate_old = max(0.0, base_tax_old - rebate_87a_old)

    # Surcharge (Old)
    surcharge_old = _calc_surcharge(ti_old, tax_after_rebate_old, is_new=False, fy="2024-25")
    tax_after_sur_old = tax_after_rebate_old + surcharge_old
    cess_old = tax_after_sur_old * 0.04
    tot_tax_old = _round_10(tax_after_sur_old + cess_old)

    old_breakdown = TaxBreakdown(
        regime="old",
        financial_year="2024-25",
        gross_salary=inp.gross_salary,
        standard_deduction=std_ded_old,
        hra_exemption=hra_ex,
        sec_24b_loss=sec_24b,
        sec_80c_allowed=sec_80c,
        sec_80ccd_1b_allowed=sec_80ccd_1b,
        sec_80d_allowed=sec_80d,
        total_deductions=total_ded_old,
        gross_total_income=gti_old,
        net_taxable_income=ti_old,
        base_tax=base_tax_old,
        rebate_87a=rebate_87a_old,
        marginal_relief_87a=0.0,
        tax_after_rebate=tax_after_rebate_old,
        surcharge=surcharge_old,
        surcharge_marginal_relief=0.0,
        tax_after_surcharge=tax_after_sur_old,
        cess=cess_old,
        total_tax_payable=tot_tax_old,
        audit_trail=traces_old
    )

    # --- NEW REGIME CALCULATION (FY 2024-25) ---
    std_ded_new = min(75000.0, inp.gross_salary)
    traces_new.append(ClauseTrace(
        section="Sec 16(ia) read with Sec 115BAC",
        description="Standard deduction under New Regime",
        amount=std_ded_new,
        legal_rule="Flat Rs. 75,000 as amended by Finance Act 2024"
    ))

    ti_new = _round_10(max(0.0, inp.gross_salary - std_ded_new))
    
    # FY 2024-25 New Slabs: 0-3L 0%, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%
    base_tax_new = 0.0
    r = ti_new
    if r > 1500000.0:
        base_tax_new += (r - 1500000.0) * 0.30
        r = 1500000.0
    if r > 1200000.0:
        base_tax_new += (r - 1200000.0) * 0.20
        r = 1200000.0
    if r > 1000000.0:
        base_tax_new += (r - 1000000.0) * 0.15
        r = 1000000.0
    if r > 700000.0:
        base_tax_new += (r - 700000.0) * 0.10
        r = 700000.0
    if r > 300000.0:
        base_tax_new += (r - 300000.0) * 0.05

    rebate_87a_new = 0.0
    marginal_relief_87a_new = 0.0
    if ti_new <= 700000.0:
        rebate_87a_new = base_tax_new
        tax_after_rebate_new = 0.0
    else:
        excess = ti_new - 700000.0
        if base_tax_new > excess:
            marginal_relief_87a_new = base_tax_new - excess
            tax_after_rebate_new = excess
        else:
            tax_after_rebate_new = base_tax_new

    # Surcharge (New Regime capped at 25%)
    surcharge_new = _calc_surcharge(ti_new, tax_after_rebate_new, is_new=True, fy="2024-25")
    tax_after_sur_new = tax_after_rebate_new + surcharge_new
    cess_new = tax_after_sur_new * 0.04
    tot_tax_new = _round_10(tax_after_sur_new + cess_new)

    new_breakdown = TaxBreakdown(
        regime="new",
        financial_year="2024-25",
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

    diff = abs(tot_tax_old - tot_tax_new)
    if tot_tax_old < tot_tax_new:
        rec = "old"
        reason = f"Old regime saves Rs. {diff:,.0f} through Chapter VI-A & HRA deductions."
    elif tot_tax_new < tot_tax_old:
        rec = "new"
        reason = f"New regime saves Rs. {diff:,.0f} due to lower slab rates."
    else:
        rec = "either"
        reason = f"Both regimes equal at Rs. {tot_tax_old:,.0f}."

    return RegimeComparison(
        old_regime=old_breakdown,
        new_regime=new_breakdown,
        recommended_regime=rec,
        tax_difference=diff,
        recommendation_reason=reason,
        is_exact_match=True
    )


def _calc_surcharge(ti: float, tax: float, is_new: bool, fy: str) -> float:
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
        rate = 0.25 if is_new else 0.37
        prev_limit = 50000000.0
        prev_rate = 0.25

    nom = tax * rate
    # Compute tax at prev_limit
    t_prev = _slab_tax(prev_limit, is_new, fy)
    max_tot = (t_prev * (1.0 + prev_rate)) + (ti - prev_limit)
    if tax + nom > max_tot:
        return max(0.0, max_tot - tax)
    return nom


def _slab_tax(inc: float, is_new: bool, fy: str) -> float:
    r = inc
    tax = 0.0
    if not is_new:
        if r > 1000000.0:
            tax += (r - 1000000.0) * 0.30
            r = 1000000.0
        if r > 500000.0:
            tax += (r - 500000.0) * 0.20
            r = 500000.0
        if r > 250000.0:
            tax += (r - 250000.0) * 0.05
    else:
        if r > 1500000.0:
            tax += (r - 1500000.0) * 0.30
            r = 1500000.0
        if r > 1200000.0:
            tax += (r - 1200000.0) * 0.20
            r = 1200000.0
        if r > 1000000.0:
            tax += (r - 1000000.0) * 0.15
            r = 1000000.0
        if r > 700000.0:
            tax += (r - 700000.0) * 0.10
            r = 700000.0
        if r > 300000.0:
            tax += (r - 300000.0) * 0.05
    return tax
