"""
Plain-Language Input Parser for Indian Income Tax Engine.
Converts conversational text (English, Hinglish, colloquial) into structured SalaryInput.
Strictly detects missing, incomplete, or contradictory information and generates
clarifying questions rather than making risky assumptions or hallucinations.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from project_a.models import SalaryInput


class ParseResult(BaseModel):
    """Result of parsing plain-language user input."""
    raw_query: str
    is_complete: bool = Field(..., description="True if sufficient unambiguous data is present")
    structured_input: Optional[SalaryInput] = None
    clarifying_questions: List[str] = Field(default_factory=list)
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    contradictions: List[str] = Field(default_factory=list)


class PlainLanguageParser:
    """Robust parser with strict ambiguity, completeness and contradiction checking."""

    def __init__(self, default_fy: str = "2024-25"):
        self.default_fy = default_fy

    def parse(self, text: str) -> ParseResult:
        """Parse raw query and return structured input or clarifying questions."""
        cleaned = text.strip()
        entities = self._extract_entities(cleaned)
        contradictions = self._detect_contradictions(entities)
        questions = []

        # 1. Contradictions take highest priority
        if contradictions:
            for c in contradictions:
                questions.append(f"Clarification needed: {c}")

        # 2. Check for missing gross salary
        gross = entities.get("gross_salary")
        if gross is None or gross <= 0:
            questions.append("What is your total annual gross salary or CTC?")

        # 3. Check for HRA ambiguity
        rent_paid = entities.get("rent_paid", 0.0)
        hra_received = entities.get("hra_received")
        basic = entities.get("basic_salary")
        city_metro = entities.get("is_metro")

        if rent_paid > 0:
            if hra_received is None:
                questions.append("You mentioned paying rent. How much actual House Rent Allowance (HRA) is included in your salary?")
            if basic is None and gross is not None:
                questions.append("What is your annual basic salary? (In India, HRA exemption depends strictly on basic salary, usually 40%-50% of CTC).")
            if city_metro is None:
                questions.append("Do you reside in a metro city (Delhi, Mumbai, Kolkata, Chennai) or a non-metro city?")

        # Check for home loan occupancy ambiguity if exceeding self-occupied cap
        home_loan_int = entities.get("home_loan_interest_24b", 0.0)
        if home_loan_int > 200000.0 and not any(k in cleaned.lower() for k in ["self occupied", "self-occupied", "own house"]):
            questions.append("Under Section 24(b), home loan interest deduction against salary is capped at Rs. 2,00,000 for self-occupied property. Please confirm if this house is self-occupied.")

        # 4. Check for parental senior citizen ambiguity
        has_parent_insurance = entities.get("sec_80d_parents", 0.0) > 0
        parents_senior = entities.get("parents_senior_citizen")
        if has_parent_insurance and parents_senior is None:
            questions.append("Are your parents senior citizens (aged 60 years or above)? This determines whether your Section 80D limit is Rs. 25,000 or Rs. 50,000.")

        # 5. Check if inquiry is asking for regime recommendation or TDS without stating any deductions
        asked_regime = any(k in cleaned.lower() for k in [
            "which regime", "old or new", "compare", "kisme fayda", "bachat",
            "tax kitna lagega", "calculate my tax", "kaun sa regime", "kaunsa regime",
            "regime accha", "which is better", "best regime", "which one", "recommend", "tds"
        ])
        has_any_deductions = any(entities.get(k, 0) > 0 for k in ["sec_80c", "sec_80ccd_1b", "sec_80d_self", "sec_80d_parents", "rent_paid", "home_loan_interest_24b"])
        explicit_zero_deductions = entities.get("explicit_zero_deductions", False)

        if asked_regime and not has_any_deductions and not explicit_zero_deductions and gross and gross > 750000:
            questions.append("To give you the most accurate Old vs New regime recommendation, do you have any investments or deductions (such as Section 80C up to 1.5L, NPS under 80CCD(1B), health insurance under 80D, or home loan interest)?")

        # Decision
        if questions:
            return ParseResult(
                raw_query=cleaned,
                is_complete=False,
                structured_input=None,
                clarifying_questions=questions,
                extracted_entities=entities,
                contradictions=contradictions
            )

        # Construct validated SalaryInput
        basic_final = basic if basic is not None else (gross * 0.50 if gross else 0.0)
        hra_final = hra_received if hra_received is not None else 0.0
        metro_final = bool(city_metro) if city_metro is not None else False

        salary_input = SalaryInput(
            gross_salary=float(gross),
            basic_salary=float(basic_final),
            hra_received=float(hra_final),
            rent_paid=float(rent_paid),
            is_metro=metro_final,
            sec_80c=float(entities.get("sec_80c", 0.0)),
            sec_80ccd_1b=float(entities.get("sec_80ccd_1b", 0.0)),
            sec_80d_self=float(entities.get("sec_80d_self", 0.0)),
            sec_80d_parents=float(entities.get("sec_80d_parents", 0.0)),
            parents_senior_citizen=bool(entities.get("parents_senior_citizen", False)),
            self_senior_citizen=bool(entities.get("self_senior_citizen", False)),
            home_loan_interest_24b=float(entities.get("home_loan_interest_24b", 0.0)),
            financial_year=entities.get("financial_year", self.default_fy)
        )

        return ParseResult(
            raw_query=cleaned,
            is_complete=True,
            structured_input=salary_input,
            clarifying_questions=[],
            extracted_entities=entities,
            contradictions=[]
        )

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract financial figures and metadata using multilingual patterns."""
        entities = {}
        t_low = text.lower()

        # Check explicit zero deductions
        if any(z in t_low for z in ["no deduction", "no rent or deduction", "no investment", "koi saving nahi", "koi deduction nahi", "no rent, no 80c", "no rent and no 80c", "no rent or investments"]):
            entities["explicit_zero_deductions"] = True

        # Extract Financial Year
        if "2025-26" in t_low or "ay 2026-27" in t_low or "fy 26" in t_low:
            entities["financial_year"] = "2025-26"
        elif "2024-25" in t_low or "ay 2025-26" in t_low or "fy 25" in t_low:
            entities["financial_year"] = "2024-25"

        # Detect Metro vs Non-Metro
        metros = ["delhi", "mumbai", "kolkata", "chennai", "bombay", "calcutta", "new delhi"]
        non_metros = ["bangalore", "bengaluru", "hyderabad", "pune", "ahmedabad", "jaipur", "noida", "gurgaon", "gurugram"]
        if any(m in t_low for m in metros):
            entities["is_metro"] = True
        elif any(nm in t_low for nm in non_metros):
            entities["is_metro"] = False

        # Senior citizen detection
        if any(p in t_low for p in ["senior citizen parent", "parents are senior", "elderly parent", "parents age 65", "father age 68", "mother age 62", "parents > 60", "parents 60+"]):
            entities["parents_senior_citizen"] = True
        elif any(p in t_low for p in ["parents are not senior", "parents age 52", "parents under 60"]):
            entities["parents_senior_citizen"] = False

        if any(s in t_low for s in ["i am senior citizen", "my age is 62", "retiree", "senior citizen age"]):
            entities["self_senior_citizen"] = True

        NUM = r"([0-9]+(?:\.[0-9]+)?)"
        UNIT = r"(lpa|lakh|lakhs|lac|lacs|cr|crore|crores|k|thousand|l)?"

        # 1. Gross Salary
        gross_patterns = [
            rf"(?:ctc|package|gross|salary|kamata|kamaata|earn|earning|income|meri salary|mera package)\s*(?:is|of|hai|of about|around)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*{UNIT}\b",
            rf"(?:rs\.?|inr|₹)\s*{NUM}\s*{UNIT}\s*(?:ctc|salary|package|gross|annual)\b",
            rf"\b{NUM}\s*{UNIT}\s*(?:salary|ctc|package|income|par|pe|ke liye)\b"
        ]
        for p in gross_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                entities["gross_salary"] = val
                break

        # 2. Basic Salary
        basic_patterns = [
            rf"(?:basic salary|basic pay|basic)\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lpa|lakh|lakhs|lac|k|pm|per month|l)?\b",
            rf"\b{NUM}\s*(?:lakh|lpa|k|l)?\s*(?:basic)\b"
        ]
        for p in basic_patterns:
            m = re.search(p, t_low)
            if m:
                unit = m.group(2) if len(m.groups()) > 1 else None
                val = self._parse_amount(m.group(1), unit)
                if unit in ["pm", "per month"]:
                    val *= 12
                entities["basic_salary"] = val
                break

        # 3. Rent Paid
        if re.search(r"\b(rent is zero|rent zero|zero rent|no rent|0 rent|rent is nil)\b", t_low):
            entities["rent_paid"] = 0.0
        else:
            rent_patterns = [
                rf"\b(?:paying rent|pay rent|rent paid|rent deta|rent bharta|rent|kiraya|monthly rent|rent of)\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(k|thousand|lakh|l|pm|per month|annual|yearly|per year)?\b",
                rf"(?<!basic is\s)(?<!salary is\s)(?<!gross is\s)(?<!package is\s)\b{NUM}\s*(lakh|lpa|l|lac|k|thousand|pm|per month)?\s*(?:saal ka|per year|annual)?\s*(?:rent|kiraya)\b"
            ]
            for p in rent_patterns:
                m = re.search(p, t_low)
                if m:
                    unit = m.group(2) if len(m.groups()) > 1 else None
                    val = self._parse_amount(m.group(1), unit)
                    if unit in ["pm", "per month"] or (val < 150000 and "year" not in t_low and "annual" not in t_low and "saal" not in t_low and val > 1000):
                        val *= 12
                    entities["rent_paid"] = val
                    break

        # 4. HRA Received
        hra_patterns = [
            rf"(?:hra received|hra allowance received|hra component|company gives hra|hra milta hai|hra deti hai|hra)\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*{UNIT}\b",
            rf"\b{NUM}\s*{UNIT}\s*(?:hra)\b"
        ]
        for p in hra_patterns:
            m = re.search(p, t_low)
            if m:
                unit = m.group(2) if len(m.groups()) > 1 else None
                val = self._parse_amount(m.group(1), unit)
                if unit in ["pm", "per month"]:
                    val *= 12
                entities["hra_received"] = val
                break

        # 5. Section 80C
        sec80c_patterns = [
            rf"(?:80c|pf|epf|ppf|elss|lic|life insurance)\s*(?:investment|me|me dalta hu|invested|contribution)?\s*(?:is|hai|of|at)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lpa|lakh|lakhs|lac|k|thousand|l)?\b",
            rf"(?:invested|investing|invest|maxed out|put)\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lpa|lakh|lakhs|lac|k|thousand|l)?\s*(?:in 80c|in ppf|in elss|in pf|80c)?\b",
            rf"\b{NUM}\s*(?:lpa|lakh|lakhs|lac|k|thousand|l)?\s*(?:in 80c|in ppf|in elss|80c)\b"
        ]
        for p in sec80c_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                if val > 0:
                    entities["sec_80c"] = val
                    break

        # 6. Section 80CCD(1B) NPS
        nps_patterns = [
            rf"(?:80ccd|nps|tier 1 nps|national pension)\s*(?:contribution|investment)?\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lpa|lakh|lakhs|lac|k|thousand|l)?\b",
            rf"\b{NUM}\s*(?:lpa|lakh|lakhs|lac|k|thousand|l)?\s*(?:in nps|in 80ccd|nps)\b"
        ]
        for p in nps_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                entities["sec_80ccd_1b"] = val
                break

        # 7. Section 80D Health Insurance (Parents)
        health_parent_patterns = [
            rf"(?:parents? health|parents mediclaim|parents insurance|maa baap ki insurance|medical insurance for parents|80d parents)\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lakh|lac|k|thousand|l)?\b",
            rf"(?:parents?|maa baap)\s*(?:ke liye|ka|ki)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(k|thousand|lakh|l)?\s*(?:mediclaim|health|insurance)\b",
            rf"\b{NUM}\s*(?:lakh|lac|k|thousand|l)?\s*(?:for parents medical insurance|for parents mediclaim|parents health insurance)\b"
        ]
        for p in health_parent_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                entities["sec_80d_parents"] = val
                break

        # 8. Section 80D Health Insurance (Self)
        health_self_patterns = [
            rf"(?:medical|health insurance|mediclaim|80d)\s*(?:for self|for family|mera|khud ka)?\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lakh|lac|k|thousand|l)?\b",
            rf"(?:took|paid|bought)\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*(lakh|lac|k|thousand|l)?\s*(?:health insurance|medical insurance|mediclaim)\b",
            rf"\b{NUM}\s*(?:lakh|lac|k|thousand|l)?\s*(?:in mediclaim|mediclaim self|80d self)\b"
        ]
        for p in health_self_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                entities["sec_80d_self"] = val
                break

        # 9. Home Loan Interest Section 24(b)
        home_loan_patterns = [
            rf"(?:home loan interest|housing loan interest|interest on housing loan|home loan emi interest)\s*(?:is|hai|of)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*{UNIT}\b",
            rf"(?:house|home loan|housing loan|loan)?\s*(?:and pay|pay|paying)?\s*(?:rs\.?|inr|₹)?\s*{NUM}\s*{UNIT}\s*(?:interest|home loan interest|housing interest)\b",
            rf"\b{NUM}\s*{UNIT}\s*(?:home loan interest|housing loan interest)\b"
        ]
        for p in home_loan_patterns:
            m = re.search(p, t_low)
            if m:
                val = self._parse_amount(m.group(1), m.group(2) if len(m.groups()) > 1 else None)
                entities["home_loan_interest_24b"] = val
                break

        return entities

    def _parse_amount(self, num_str: str, unit_str: Optional[str]) -> float:
        """Convert string number + denomination into absolute rupees."""
        try:
            num = float(num_str)
        except ValueError:
            return 0.0

        if not unit_str:
            return num

        u = unit_str.lower().strip()
        if u in ["l", "lpa", "lakh", "lakhs", "lac", "lacs"]:
            return num * 100000.0
        elif u in ["cr", "crore", "crores"]:
            return num * 10000000.0
        elif u in ["k", "thousand"]:
            return num * 1000.0
        return num

    def _detect_contradictions(self, entities: Dict[str, Any]) -> List[str]:
        """Detect logical and statutory impossibilities."""
        contradictions = []
        gross = entities.get("gross_salary")

        # 1. Deductions exceeding gross salary
        sec_80c = entities.get("sec_80c", 0.0)
        if gross and sec_80c > gross:
            contradictions.append(f"Section 80C investment claimed (Rs.{sec_80c:,.0f}) cannot exceed your total gross salary (Rs.{gross:,.0f}).")

        # 2. Rent paid exceeding gross salary
        rent = entities.get("rent_paid", 0.0)
        if gross and rent > gross:
            contradictions.append(f"Annual rent paid (Rs.{rent:,.0f}) cannot exceed your entire annual salary (Rs.{gross:,.0f}).")

        # 3. Basic salary exceeding gross salary
        basic = entities.get("basic_salary")
        if gross and basic and basic > gross:
            contradictions.append(f"Basic salary (Rs.{basic:,.0f}) cannot exceed gross salary (Rs.{gross:,.0f}).")

        # 4. HRA received exceeding gross salary
        hra = entities.get("hra_received")
        if gross and hra and hra > gross:
            contradictions.append(f"HRA allowance (Rs.{hra:,.0f}) cannot exceed total gross salary (Rs.{gross:,.0f}).")

        return contradictions
