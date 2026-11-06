"""
Pydantic data models for Indian Income Tax Engine (Project A).
Supports both FY 2024-25 (AY 2025-26) and FY 2025-26 (AY 2026-27).
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SalaryInput(BaseModel):
    """Structured input parameters for salaried individual."""
    gross_salary: float = Field(..., ge=0, description="Gross annual salary including allowances and perquisites")
    basic_salary: float = Field(..., ge=0, description="Annual basic salary (used for HRA exemption calculation)")
    hra_received: float = Field(0.0, ge=0, description="Actual annual House Rent Allowance received")
    rent_paid: float = Field(0.0, ge=0, description="Actual annual rent paid for residential accommodation")
    is_metro: bool = Field(False, description="True if residing in Delhi, Mumbai, Kolkata, or Chennai (50% rule)")
    
    # Chapter VI-A & Other Deductions
    sec_80c: float = Field(0.0, ge=0, description="Section 80C investments (EPF, PPF, ELSS, life insurance, principal loan repayment)")
    sec_80ccd_1b: float = Field(0.0, ge=0, description="Section 80CCD(1B) NPS employee voluntary contribution")
    sec_80d_self: float = Field(0.0, ge=0, description="Section 80D health insurance for self, spouse, children")
    sec_80d_parents: float = Field(0.0, ge=0, description="Section 80D health insurance for parents")
    parents_senior_citizen: bool = Field(False, description="Whether parents are senior citizens (>= 60 years)")
    self_senior_citizen: bool = Field(False, description="Whether taxpayer is senior citizen (>= 60 years)")
    home_loan_interest_24b: float = Field(0.0, ge=0, description="Interest on housing loan for self-occupied house (Section 24(b))")
    
    # Financial Year
    financial_year: str = Field("2024-25", description="Financial year, e.g. '2024-25' or '2025-26'")


class ClauseTrace(BaseModel):
    """Traces a specific rupee amount to its statutory clause."""
    section: str = Field(..., description="Act and Section reference, e.g. 'Section 16(ia)'")
    description: str = Field(..., description="Plain-language description of the rule/allowance")
    amount: float = Field(..., description="Rupee impact or calculated deduction/tax")
    legal_rule: str = Field(..., description="Exact statutory condition or formula applied")


class TaxBreakdown(BaseModel):
    """Itemized tax computation breakdown for a regime."""
    regime: str = Field(..., description="'old' or 'new'")
    financial_year: str = Field(..., description="'2024-25' or '2025-26'")
    gross_salary: float
    
    # Deductions
    standard_deduction: float
    hra_exemption: float
    sec_24b_loss: float
    sec_80c_allowed: float
    sec_80ccd_1b_allowed: float
    sec_80d_allowed: float
    total_deductions: float
    
    # Taxable Income
    gross_total_income: float
    net_taxable_income: float  # Rounded to nearest 10 under Sec 288A
    
    # Tax Calculations
    base_tax: float
    rebate_87a: float
    marginal_relief_87a: float
    tax_after_rebate: float
    surcharge: float
    surcharge_marginal_relief: float
    tax_after_surcharge: float
    cess: float  # 4%
    total_tax_payable: float  # Rounded to nearest 10 under Sec 288B
    
    # Statutory Audit Trail
    audit_trail: List[ClauseTrace] = Field(default_factory=list)


class RegimeComparison(BaseModel):
    """Comparative recommendation between Old and New regimes."""
    old_regime: TaxBreakdown
    new_regime: TaxBreakdown
    recommended_regime: str  # 'old', 'new', or 'either'
    tax_difference: float  # Absolute savings
    recommendation_reason: str
    is_exact_match: bool = True
