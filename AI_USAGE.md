# AI_USAGE.md — Disclosure of AI Tooling & Verification Case Study

**Candidate:** Soumya Ranjan Patra  
**Hiring Organization:** Fire AI  
**Assignment:** Rules vs LLMs Take-Home Assignment  

---

## 1. AI Tools Used and Their Respective Roles

In accordance with the assignment guidelines (*"AI tools are allowed and expected. Use LLMs, coding agents, Copilot, anything, to write your code. You must be able to explain and change every line you submit."*), the following tools and models were utilized:

| AI Tool / Model | Workflow Stage / Scope | Specific Responsibility |
| :--- | :--- | :--- |
| **Antigravity Coding Agent (Gemini 3.8 Flash High)** | System Architecture & Scaffolding | Generating initial file boilerplate, data models (Pydantic), and test runner scaffolds. |
| **Gemini 1.5 Flash (Google GenAI SDK)** | Project A: Query-Time LLM & LLM Compiler | Benchmark target for query-time statutory tax interpretation and offline AST compilation. |
| **Gemini 1.5 Flash (Google GenAI SDK)** | Project B: LLM Review Detector | Semantic auditing of complaint type vs descriptor coherence and unstructured PII detection. |
| **Python Regex & AST Tooling** | Grammar & Rule Engine Design | Validating statutory AST representations and constructing multilingual plain-language tokenizers. |

---

## 2. Case Study: Where the AI was Wrong and How It Was Caught

Rigorous engineering requires treating all AI outputs as untrusted candidate inputs subject to strict empirical verification. Below are two concrete instances where the AI generated incorrect logic and how automated test suites caught the defect:

### Case 1: Arithmetic Deduction Hallucination in Benchmark Dataset

- **Where the AI was used**: Generating the initial 30 official Income Tax Department (ITD) benchmark test cases for cross-validation in `generate_test_cases.py`.
- **What the AI produced**: For benchmark case `OFFICIAL_10` (Salaried individual earning ₹10,00,000 gross salary, claiming ₹1,50,000 in Section 80C and ₹25,000 in Section 80D health insurance), the AI asserted that the expected Old Regime tax liability was **₹67,600**.
- **How it was caught**:
  When we executed the deterministic test harness (`pytest project_a/test_suite/test_project_a.py`), both our Hand-coded engine and Compiled rule engine failed with an assertion error:
  ```
  AssertionError: Failed on OFFICIAL_10: Expected Old Tax 67600.0, got 70200.0
  ```
- **Root Cause Analysis**:
  We manually traced the statutory arithmetic:
  1. Gross Salary: ₹10,00,000
  2. Section 16(ia) Standard Deduction: ₹50,000
  3. Section 80C Allowed: ₹1,50,000
  4. Section 80D Allowed: ₹25,000
  5. Total Statutory Deductions: $50,000 + 150,000 + 25,000 = \mathbf{₹2,25,000}$
  6. Net Taxable Income: $10,00,000 - 2,25,000 = \mathbf{₹7,75,000}$
  7. Slab Tax Computation:
     - ₹0 to ₹2,50,000 @ 0% = ₹0
     - ₹2,50,001 to ₹5,00,000 @ 5% = ₹12,500
     - ₹5,00,001 to ₹7,75,000 @ 20% on ₹2,75,000 = ₹55,000
     - Base Tax: $12,500 + 55,000 = \mathbf{₹67,500}$
  8. Health & Education Cess (4% on ₹67,500): $\mathbf{₹2,700}$
  9. Total Tax Payable: $67,500 + 2,700 = \mathbf{₹70,200}$
  
  The AI model had mentally deducted ₹2,50,000 instead of ₹2,25,000, calculating tax on ₹7,50,000 ($65,000 + 4\% = 67,600$). 
- **Remediation**:
  We rejected the AI's hallucinated number, programmed the automated benchmark generator to derive reference targets directly from validated statutory logic, and cross-verified against the official ITD utility.

---

### Case 2: Substring Collision in Regular Expression Tokenizer

- **Where the AI was used**: Generating the entity extraction regex in `project_a/parser.py` to identify whether a user paid zero rent.
- **What the AI produced**:
  ```python
  if any(zr in text for zr in ["rent is zero", "zero rent", "no rent", "0 rent", "rent is nil"]):
      entities["rent_paid"] = 0.0
  ```
- **What went wrong**:
  When evaluating user query `PL_28`:
  > *"My CTC is 18 LPA and I pay 35000 rent per month."*
  
  The substring `"0 rent"` matched inside `"35000 rent"` (the trailing `0` of `35000` combined with ` rent`)!
  Consequently, the parser extracted `rent_paid = 0.0`, treating the user as paying zero rent instead of ₹35,000/month, and erroneously marked the query as complete without asking for HRA and city details.
- **How it was caught**:
  Our automated test suite `test_plain_language_parser` asserted that `PL_28` must be flagged as incomplete (`is_complete == False`) because paying rent without specifying HRA or basic salary requires clarification. The test failed immediately with:
  ```
  AssertionError: Expected PL_28 to require clarification. Got is_complete=True with rent_paid=0.0
  ```
- **Remediation**:
  We replaced the naive substring check with strict regex word boundaries:
  ```python
  if re.search(r"\b(rent is zero|rent zero|zero rent|no rent|\b0 rent|rent is nil)\b", text):
      entities["rent_paid"] = 0.0
  ```
  This immediately resolved the false positive, ensuring `"35000 rent"` was correctly parsed as ₹4,20,000 annual rent and triggered the mandatory HRA clarification question.

---

## 3. Defense Interview Readiness

Every line of code across `project_a/` and `project_b/` was audited, refactored, and tested to ensure complete human understanding. During the 60-minute defense interview, I am prepared to:
1. Live-code statutory modifications (e.g., changes to Section 80CCD(2) employer NPS limits or alterations to surcharge marginal relief formulas).
2. Adapt the data-quality pipeline live to handle novel data corruptions (e.g., timezone shifts, multi-tenant schema migrations, or streaming window variations).
3. Defend all architectural choices with empirical benchmark numbers and operational telemetry.
