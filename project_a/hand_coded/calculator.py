"""
Hand-coded deterministic tax rule engine for Indian salaried taxpayers.
Implements FY 2024-25 and FY 2025-26 rules with full statutory clause traceability.
"""

from typing import Tuple, List
from project_a.models import SalaryInput, TaxBreakdown, RegimeComparison, ClauseTrace


def round_nearest_10(val: float) -> float:
    """Rounds to nearest multiple of 10 according to Sections 288A and 288B."""
    remainder = val % 10
    if remainder >= 5:
        return float(int(val // 10 + 1) * 10)
    else:
        return float(int(val // 10) * 10)


class HandCodedTaxEngine:
    """Deterministic rule engine for Indian Income Tax computation."""

    def __init__(self, financial_year: str = "2024-25"):
        self.fy = financial_year

    def compute_hra_exemption(self, inp: SalaryInput) -> Tuple[float, List[ClauseTrace]]:
        """
        Compute HRA exemption under Section 10(13A) read with Rule 2A.
        Exemption is least of:
          1. Actual HRA received
          2. Rent paid - 10% of basic salary
          3. 50% of basic salary (metro) or 40% (non-metro)
        """
        traces = []
        if inp.hra_received <= 0 or inp.rent_paid <= 0 or inp.basic_salary <= 0:
            traces.append(ClauseTrace(
                section="Section 10(13A)",
                description="HRA exemption",
                amount=0.0,
                legal_rule="No exemption as HRA received or rent paid is zero"
            ))
            return 0.0, traces

        limit_1 = inp.hra_received
        limit_2 = max(0.0, inp.rent_paid - (0.10 * inp.basic_salary))
        metro_rate = 0.50 if inp.is_metro else 0.40
        limit_3 = metro_rate * inp.basic_salary

        exempt_amount = min(limit_1, limit_2, limit_3)
        city_desc = "Metro (50%)" if inp.is_metro else "Non-Metro (40%)"
        traces.append(ClauseTrace(
            section="Section 10(13A) / Rule 2A",
            description="HRA Exemption",
            amount=exempt_amount,
            legal_rule=f"Min of: Actual HRA (Rs.{limit_1:.0f}), Rent - 10% basic (Rs.{limit_2:.0f}), {city_desc} (Rs.{limit_3:.0f})"
        ))
        return exempt_amount, traces

    def compute_old_regime(self, inp: SalaryInput) -> TaxBreakdown:
        """Compute tax under Old Tax Regime."""
        traces = []
        
        # 1. Standard deduction (Section 16(ia))
        std_ded = min(50000.0, inp.gross_salary)
        traces.append(ClauseTrace(
            section="Section 16(ia)",
            description="Standard deduction for salaried employees",
            amount=std_ded,
            legal_rule="Flat deduction of Rs. 50,000 or actual gross salary, whichever is less"
        ))

        # 2. HRA Exemption (Section 10(13A))
        hra_ex, hra_traces = self.compute_hra_exemption(inp)
        traces.extend(hra_traces)

        # 3. Home loan interest (Section 24(b))
        sec_24b = min(200000.0, inp.home_loan_interest_24b)
        if sec_24b > 0:
            traces.append(ClauseTrace(
                section="Section 24(b)",
                description="Interest on loan for self-occupied house",
                amount=sec_24b,
                legal_rule="Capped at maximum Rs. 2,00,000 for self-occupied residential property"
            ))

        # 4. Chapter VI-A deductions
        # Section 80C
        sec_80c_allowed = min(150000.0, inp.sec_80c)
        if sec_80c_allowed > 0:
            traces.append(ClauseTrace(
                section="Section 80C",
                description="Investments in EPF, PPF, ELSS, Life Insurance, etc.",
                amount=sec_80c_allowed,
                legal_rule="Aggregate deduction capped at Rs. 1,50,000"
            ))

        # Section 80CCD(1B)
        sec_80ccd_1b_allowed = min(50000.0, inp.sec_80ccd_1b)
        if sec_80ccd_1b_allowed > 0:
            traces.append(ClauseTrace(
                section="Section 80CCD(1B)",
                description="NPS employee voluntary contribution",
                amount=sec_80ccd_1b_allowed,
                legal_rule="Additional deduction capped at Rs. 50,000"
            ))

        # Section 80D
        limit_self = 50000.0 if inp.self_senior_citizen else 25000.0
        limit_parents = 50000.0 if inp.parents_senior_citizen else 25000.0
        sec_80d_self_allowed = min(limit_self, inp.sec_80d_self)
        sec_80d_parents_allowed = min(limit_parents, inp.sec_80d_parents)
        sec_80d_allowed = sec_80d_self_allowed + sec_80d_parents_allowed
        if sec_80d_allowed > 0:
            traces.append(ClauseTrace(
                section="Section 80D",
                description="Health insurance premium (self and parents)",
                amount=sec_80d_allowed,
                legal_rule=f"Self limit Rs.{limit_self:.0f}, Parents limit Rs.{limit_parents:.0f}"
            ))

        # Total deductions
        total_ded = std_ded + hra_ex + sec_24b + sec_80c_allowed + sec_80ccd_1b_allowed + sec_80d_allowed
        gti = max(0.0, inp.gross_salary - std_ded - hra_ex - sec_24b)
        net_taxable_unrounded = max(0.0, inp.gross_salary - total_ded)
        net_taxable = round_nearest_10(net_taxable_unrounded)
        traces.append(ClauseTrace(
            section="Section 288A",
            description="Net taxable income rounded off",
            amount=net_taxable,
            legal_rule="Rounded off to nearest multiple of Rs. 10"
        ))

        # Base tax computation under Old Slabs
        base_tax = 0.0
        first_slab_limit = 300000.0 if inp.self_senior_citizen else 250000.0
        rem = net_taxable

        if rem > 1000000.0:
            base_tax += (rem - 1000000.0) * 0.30
            rem = 1000000.0
        if rem > 500000.0:
            base_tax += (rem - 500000.0) * 0.20
            rem = 500000.0
        if rem > first_slab_limit:
            base_tax += (rem - first_slab_limit) * 0.05

        traces.append(ClauseTrace(
            section="First Schedule, Part I (Old Regime)",
            description="Income tax at slab rates",
            amount=base_tax,
            legal_rule="Slabs: 0-2.5L: 0%, 2.5-5L: 5%, 5-10L: 20%, >10L: 30%"
        ))

        # Section 87A Rebate (Old Regime: Net Taxable Income <= 5,00,000)
        rebate_87a = 0.0
        if net_taxable <= 500000.0:
            rebate_87a = min(base_tax, 12500.0)
            traces.append(ClauseTrace(
                section="Section 87A",
                description="Tax rebate for income up to Rs. 5,00,000",
                amount=rebate_87a,
                legal_rule="100% of tax or Rs. 12,500, whichever is less"
            ))

        tax_after_rebate = max(0.0, base_tax - rebate_87a)

        # Surcharge & Marginal Relief
        surcharge, sur_traces = self._compute_surcharge(net_taxable, tax_after_rebate, is_new_regime=False)
        traces.extend(sur_traces)

        tax_after_surcharge = tax_after_rebate + surcharge

        # Cess 4%
        cess = tax_after_surcharge * 0.04
        traces.append(ClauseTrace(
            section="Finance Act (Health and Education Cess)",
            description="Health and Education Cess @ 4%",
            amount=cess,
            legal_rule="4% on aggregate of income tax and surcharge"
        ))

        total_tax = round_nearest_10(tax_after_surcharge + cess)
        traces.append(ClauseTrace(
            section="Section 288B",
            description="Total tax liability rounded off",
            amount=total_tax,
            legal_rule="Rounded off to nearest multiple of Rs. 10"
        ))

        return TaxBreakdown(
            regime="old",
            financial_year=self.fy,
            gross_salary=inp.gross_salary,
            standard_deduction=std_ded,
            hra_exemption=hra_ex,
            sec_24b_loss=sec_24b,
            sec_80c_allowed=sec_80c_allowed,
            sec_80ccd_1b_allowed=sec_80ccd_1b_allowed,
            sec_80d_allowed=sec_80d_allowed,
            total_deductions=total_ded,
            gross_total_income=gti,
            net_taxable_income=net_taxable,
            base_tax=base_tax,
            rebate_87a=rebate_87a,
            marginal_relief_87a=0.0,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            surcharge_marginal_relief=0.0,
            tax_after_surcharge=tax_after_surcharge,
            cess=cess,
            total_tax_payable=total_tax,
            audit_trail=traces
        )

    def compute_new_regime(self, inp: SalaryInput) -> TaxBreakdown:
        """Compute tax under New Tax Regime (Section 115BAC)."""
        traces = []
        
        # 1. Standard deduction (Section 16(ia))
        # FY 2024-25 and FY 2025-26: Rs. 75,000
        std_ded_limit = 75000.0
        std_ded = min(std_ded_limit, inp.gross_salary)
        traces.append(ClauseTrace(
            section="Section 16(ia) read with Sec 115BAC",
            description="Standard deduction under new tax regime",
            amount=std_ded,
            legal_rule=f"Flat Rs. {std_ded_limit:.0f} or gross salary, whichever is lower"
        ))

        # No HRA, No 24b, No 80C/80D/80CCD(1B)
        total_ded = std_ded
        gti = max(0.0, inp.gross_salary - std_ded)
        net_taxable = round_nearest_10(gti)
        traces.append(ClauseTrace(
            section="Section 288A",
            description="Net taxable income rounded off",
            amount=net_taxable,
            legal_rule="Rounded off to nearest multiple of Rs. 10"
        ))

        # Tax slabs
        base_tax = 0.0
        marginal_relief_87a = 0.0
        rebate_87a = 0.0

        if self.fy == "2024-25":
            # FY 2024-25 New Regime Slabs:
            # 0 - 3L: Nil
            # 3L - 7L: 5% (max 20,000)
            # 7L - 10L: 10% (max 30,000)
            # 10L - 12L: 15% (max 30,000)
            # 12L - 15L: 20% (max 60,000)
            # > 15L: 30%
            rem = net_taxable
            if rem > 1500000.0:
                base_tax += (rem - 1500000.0) * 0.30
                rem = 1500000.0
            if rem > 1200000.0:
                base_tax += (rem - 1200000.0) * 0.20
                rem = 1200000.0
            if rem > 1000000.0:
                base_tax += (rem - 1000000.0) * 0.15
                rem = 1000000.0
            if rem > 700000.0:
                base_tax += (rem - 700000.0) * 0.10
                rem = 700000.0
            if rem > 300000.0:
                base_tax += (rem - 300000.0) * 0.05

            traces.append(ClauseTrace(
                section="Section 115BAC(1A)",
                description="New regime slab tax (FY 2024-25)",
                amount=base_tax,
                legal_rule="Slabs: 0-3L 0%, 3-7L 5%, 7-10L 10%, 10-12L 15%, 12-15L 20%, >15L 30%"
            ))

            # Rebate 87A and Marginal Relief
            if net_taxable <= 700000.0:
                rebate_87a = base_tax
                traces.append(ClauseTrace(
                    section="Section 87A (New Regime)",
                    description="Rebate for income up to Rs. 7,00,000",
                    amount=rebate_87a,
                    legal_rule="Full tax rebate up to Rs. 25,000 if taxable income <= 7,00,000"
                ))
                tax_after_rebate = 0.0
            else:
                # Marginal relief for income slightly exceeding Rs. 7,00,000:
                # Tax cannot exceed (Total Income - 7,00,000)
                excess_income = net_taxable - 700000.0
                if base_tax > excess_income:
                    marginal_relief_87a = base_tax - excess_income
                    tax_after_rebate = excess_income
                    traces.append(ClauseTrace(
                        section="Section 87A Proviso (Marginal Relief)",
                        description="Marginal relief on Section 87A",
                        amount=marginal_relief_87a,
                        legal_rule=f"Tax capped at excess income over 7L (Rs. {excess_income:.0f})"
                    ))
                else:
                    tax_after_rebate = base_tax

        elif self.fy == "2025-26":
            # FY 2025-26 New Regime Slabs (Finance Act 2025):
            # 0 - 4L: Nil
            # 4L - 8L: 5% (max 20,000)
            # 8L - 12L: 10% (max 40,000)
            # 12L - 16L: 15% (max 60,000)
            # 16L - 20L: 20% (max 80,000)
            # 20L - 24L: 25% (max 1,00,000)
            # > 24L: 30%
            rem = net_taxable
            if rem > 2400000.0:
                base_tax += (rem - 2400000.0) * 0.30
                rem = 2400000.0
            if rem > 2000000.0:
                base_tax += (rem - 2000000.0) * 0.25
                rem = 2000000.0
            if rem > 1600000.0:
                base_tax += (rem - 1600000.0) * 0.20
                rem = 1600000.0
            if rem > 1200000.0:
                base_tax += (rem - 1200000.0) * 0.15
                rem = 1200000.0
            if rem > 800000.0:
                base_tax += (rem - 800000.0) * 0.10
                rem = 800000.0
            if rem > 400000.0:
                base_tax += (rem - 400000.0) * 0.05

            traces.append(ClauseTrace(
                section="Section 115BAC(1A) (FY 2025-26)",
                description="New regime slab tax (FY 2025-26)",
                amount=base_tax,
                legal_rule="Slabs: 0-4L 0%, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, >24L 30%"
            ))

            # Rebate 87A for FY 2025-26: up to 12,00,000
            if net_taxable <= 1200000.0:
                rebate_87a = base_tax
                traces.append(ClauseTrace(
                    section="Section 87A (FY 2025-26)",
                    description="Full rebate for income up to Rs. 12,00,000",
                    amount=rebate_87a,
                    legal_rule="Full tax rebate if taxable income <= 12,00,000"
                ))
                tax_after_rebate = 0.0
            else:
                excess_income = net_taxable - 1200000.0
                if base_tax > excess_income:
                    marginal_relief_87a = base_tax - excess_income
                    tax_after_rebate = excess_income
                    traces.append(ClauseTrace(
                        section="Section 87A Proviso (Marginal Relief FY 2025-26)",
                        description="Marginal relief on Section 87A",
                        amount=marginal_relief_87a,
                        legal_rule=f"Tax capped at excess income over 12L (Rs. {excess_income:.0f})"
                    ))
                else:
                    tax_after_rebate = base_tax
        else:
            raise ValueError(f"Unsupported financial year: {self.fy}")

        # Surcharge & Marginal Relief (New regime capped at 25%)
        surcharge, sur_traces = self._compute_surcharge(net_taxable, tax_after_rebate, is_new_regime=True)
        traces.extend(sur_traces)

        tax_after_surcharge = tax_after_rebate + surcharge

        # Cess 4%
        cess = tax_after_surcharge * 0.04
        traces.append(ClauseTrace(
            section="Finance Act (Health and Education Cess)",
            description="Health and Education Cess @ 4%",
            amount=cess,
            legal_rule="4% on aggregate of income tax and surcharge"
        ))

        total_tax = round_nearest_10(tax_after_surcharge + cess)
        traces.append(ClauseTrace(
            section="Section 288B",
            description="Total tax liability rounded off",
            amount=total_tax,
            legal_rule="Rounded off to nearest multiple of Rs. 10"
        ))

        return TaxBreakdown(
            regime="new",
            financial_year=self.fy,
            gross_salary=inp.gross_salary,
            standard_deduction=std_ded,
            hra_exemption=0.0,
            sec_24b_loss=0.0,
            sec_80c_allowed=0.0,
            sec_80ccd_1b_allowed=0.0,
            sec_80d_allowed=0.0,
            total_deductions=total_ded,
            gross_total_income=gti,
            net_taxable_income=net_taxable,
            base_tax=base_tax,
            rebate_87a=rebate_87a,
            marginal_relief_87a=marginal_relief_87a,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            surcharge_marginal_relief=0.0,
            tax_after_surcharge=tax_after_surcharge,
            cess=cess,
            total_tax_payable=total_tax,
            audit_trail=traces
        )

    def _compute_surcharge(self, taxable_income: float, tax_amount: float, is_new_regime: bool) -> Tuple[float, List[ClauseTrace]]:
        """
        Compute statutory surcharge and marginal relief.
        Thresholds:
          50L - 1Cr: 10%
          1Cr - 2Cr: 15%
          2Cr - 5Cr: 25%
          > 5Cr: Old Regime 37%, New Regime capped at 25%
        """
        traces = []
        if taxable_income <= 5000000.0 or tax_amount <= 0:
            return 0.0, traces

        rate = 0.0
        limit = 0.0
        prev_limit = 0.0
        prev_rate = 0.0

        if taxable_income <= 10000000.0:
            rate = 0.10
            limit = 5000000.0
            prev_limit = 5000000.0
            prev_rate = 0.0
        elif taxable_income <= 20000000.0:
            rate = 0.15
            limit = 10000000.0
            prev_limit = 10000000.0
            prev_rate = 0.10
        elif taxable_income <= 50000000.0:
            rate = 0.25
            limit = 20000000.0
            prev_limit = 20000000.0
            prev_rate = 0.15
        else:
            rate = 0.25 if is_new_regime else 0.37
            limit = 50000000.0
            prev_limit = 50000000.0
            prev_rate = 0.25

        nominal_surcharge = tax_amount * rate

        # Marginal relief calculation:
        # Total (tax + surcharge) on taxable_income cannot exceed:
        # [Tax on prev_limit + (Tax on prev_limit * prev_rate)] + (taxable_income - prev_limit)
        tax_at_prev_limit = self._tax_on_income(prev_limit, is_new_regime)
        max_total = (tax_at_prev_limit * (1.0 + prev_rate)) + (taxable_income - prev_limit)
        current_total = tax_amount + nominal_surcharge

        if current_total > max_total:
            surcharge = max(0.0, max_total - tax_amount)
            relief = nominal_surcharge - surcharge
            traces.append(ClauseTrace(
                section="Chapter II (Surcharge & Marginal Relief)",
                description=f"Surcharge with marginal relief ({int(rate*100)}% tier)",
                amount=surcharge,
                legal_rule=f"Nominal surcharge Rs.{nominal_surcharge:.0f} reduced by marginal relief Rs.{relief:.0f}"
            ))
        else:
            surcharge = nominal_surcharge
            traces.append(ClauseTrace(
                section="Chapter II (Surcharge)",
                description=f"Surcharge @ {int(rate*100)}%",
                amount=surcharge,
                legal_rule=f"{int(rate*100)}% surcharge on tax Rs.{tax_amount:.0f}"
            ))

        return surcharge, traces

    def _tax_on_income(self, income: float, is_new_regime: bool) -> float:
        """Helper to compute slab tax on a baseline income threshold."""
        rem = income
        tax = 0.0
        if not is_new_regime:
            if rem > 1000000.0:
                tax += (rem - 1000000.0) * 0.30
                rem = 1000000.0
            if rem > 500000.0:
                tax += (rem - 500000.0) * 0.20
                rem = 500000.0
            if rem > 250000.0:
                tax += (rem - 250000.0) * 0.05
        else:
            if self.fy == "2024-25":
                if rem > 1500000.0:
                    tax += (rem - 1500000.0) * 0.30
                    rem = 1500000.0
                if rem > 1200000.0:
                    tax += (rem - 1200000.0) * 0.20
                    rem = 1200000.0
                if rem > 1000000.0:
                    tax += (rem - 1000000.0) * 0.15
                    rem = 1000000.0
                if rem > 700000.0:
                    tax += (rem - 700000.0) * 0.10
                    rem = 700000.0
                if rem > 300000.0:
                    tax += (rem - 300000.0) * 0.05
            else:
                if rem > 2400000.0:
                    tax += (rem - 2400000.0) * 0.30
                    rem = 2400000.0
                if rem > 2000000.0:
                    tax += (rem - 2000000.0) * 0.25
                    rem = 2000000.0
                if rem > 1600000.0:
                    tax += (rem - 1600000.0) * 0.20
                    rem = 1600000.0
                if rem > 1200000.0:
                    tax += (rem - 1200000.0) * 0.15
                    rem = 1200000.0
                if rem > 800000.0:
                    tax += (rem - 800000.0) * 0.10
                    rem = 800000.0
                if rem > 400000.0:
                    tax += (rem - 400000.0) * 0.05
        return tax

    def compare(self, inp: SalaryInput) -> RegimeComparison:
        """Run both regimes and provide statutory comparison and recommendation."""
        old_res = self.compute_old_regime(inp)
        new_res = self.compute_new_regime(inp)

        diff = abs(old_res.total_tax_payable - new_res.total_tax_payable)
        if old_res.total_tax_payable < new_res.total_tax_payable:
            rec = "old"
            reason = f"Old Regime saves Rs. {diff:,.0f} due to high deductions (HRA, 80C, 80D, etc.) exceeding standard deduction advantage."
        elif new_res.total_tax_payable < old_res.total_tax_payable:
            rec = "new"
            reason = f"New Regime saves Rs. {diff:,.0f} due to lower slab tax rates and higher standard deduction (Rs. 75,000)."
        else:
            rec = "either"
            reason = f"Both regimes result in identical tax liability of Rs. {old_res.total_tax_payable:,.0f}."

        return RegimeComparison(
            old_regime=old_res,
            new_regime=new_res,
            recommended_regime=rec,
            tax_difference=diff,
            recommendation_reason=reason,
            is_exact_match=True
        )
