# Rules vs LLMs Take-Home Assignment — Fire AI

**Candidate:** Soumya Ranjan Patra  
**Hiring Organization:** Fire AI  
**Assignment Period:** Oct 2026  
**Language:** Python 3.10+  

---

## Overview

This repository implements the complete solutions for **Project A (Income-Tax Engine: Rules, LLM or Both?)** and **Project B (Data-Quality Checks: Rules, Statistics or LLM Review?)** as specified in the Fire AI Rules vs LLMs Take-Home Assignment.

The core principle evaluated is:
> *"Deciding when a deterministic rule is the right tool, when an LLM earns its cost, and when the answer is a combination of both. There is no prize for using the most AI. A design that uses an LLM in only the few places it is genuinely better, and can prove it, will score highest."*

---

## Deliverables Index

In accordance with the submission deliverables specification:

| Deliverable | File Path | Description |
| :--- | :--- | :--- |
| **Project A Code** | [`project_a/`](project_a/) | Hand-coded rules, LLM at query time, LLM-compiled rules, plain-language parser, and test suite. |
| **Project A Results** | [`RESULTS_A.md`](RESULTS_A.md) | Comparison benchmark table, Task 5 Finance Act 2025 change log, and final 100,000-user system architecture. |
| **Project B Code** | [`project_b/`](project_b/) | Raw 2023 NYC 311 data profiler, 12-problem corruption injector, 3 detector families, and hybrid pipeline. |
| **Project B Results** | [`RESULTS_B.md`](RESULTS_B.md) | Per-problem detection & cost table, real 2023 NYC 311 issues found, and 50M rows/day scale design across 120 tenants. |
| **Decision Matrix** | [`DECISION_MATRIX.md`](DECISION_MATRIX.md) | Unified matrix with one row per component/check, marked Rule/Statistical/LLM/Hybrid with empirical measurements. |
| **AI Usage Note** | [`AI_USAGE.md`](AI_USAGE.md) | Disclosure of tools used, roles, and a concrete case study where the AI was wrong and how it was caught. |

---

## Quickstart & Single-Command Reproduction

The assignment mandates:
> *"Submit one private repo in which a single command reproduces every number you report."*

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/soumyaranjan4446/rules-vs-llms.git
cd rules-vs-llms

# Install dependencies
pip install -r requirements.txt
```

### 2. Single-Command Full Reproduction
Execute the master runner to reproduce every benchmark table, run all simulations, and verify metrics across both projects:
```bash
python run_all.py
```

### 3. Automated Test Suite (Pytest)
Run the full automated test suite (official calculator cross-checks, edge cases, parser dialogs, and detector tests):
```bash
python -m pytest -v
```

---

## Project A: Income-Tax Engine Summary

- **Scope**: Salaried individuals in India for **FY 2024-25** and **FY 2025-26** (Finance Act 2025). Covers standard deduction, Section 10(13A) HRA Rule 2A, Section 80C, Section 80CCD(1B), Section 80D (senior parents), Section 24(b) home loan caps, Section 87A rebate & marginal relief, surcharge with marginal relief up to ₹10 Crore, and 4% cess.
- **Three Implementations Evaluated**:
  1. *Hand-coded rules*: 100% rupee-exact accuracy, 0.035 ms latency, $0.00 cost, 100% deterministic, 100% clause traceability.
  2. *LLM-compiled rules*: 100% rupee-exact accuracy, 0.022 ms latency, $0.00 runtime cost, 100% deterministic, audited AST.
  3. *LLM at query time*: 78.4% accuracy (fails at marginal relief arithmetic and rounding), ~740 ms latency, $0.18/1k requests, 35% traceability.
- **Plain-Language Parser**: Robust entity extraction across English, Hinglish, and colloquial queries. When queries are ambiguous (missing basic salary for HRA, missing metro status, or incomplete deduction disclosures), the system **asks targeted clarifying questions instead of guessing**.
- **Task 5 (Law Changes)**: When Finance Act 2025 revised New Regime slabs and raised the Section 87A rebate to ₹12L, the query-time LLM suffered **critical silent failures** (hallucinating old slabs and miscalculating marginal relief without throwing errors), whereas Hand-Coded and Compiled rules caught all discrepancies loudly in tests.

---

## Project B: NYC 311 Data-Quality Firewall Summary

- **Dataset**: Real 2023 NYC 311 Service Requests from NYC Open Data (`erm2-nwe9`).
- **Real 2023 Quality Issues Found**:
  - 9 tickets closed *before* they were created (negative duration).
  - 179 tickets (3.98%) leaking citizen telephone numbers in resolution free-text.
  - 62 records missing coordinates; 43 records missing postal codes.
- **12 Problem Types Benchmarked**:
  1. Renamed or dropped column *(Winner: Declarative Rules — 100% recall)*
  2. Column type mutation *(Winner: Declarative Rules — 100% recall)*
  3. Date format switch *(Winner: Declarative Rules — 100% recall)*
  4. Latitude and longitude swapped *(Winner: Declarative Rules — 100% recall)*
  5. Exact duplicates *(Winner: Declarative Rules — 100% recall)*
  6. Near-duplicates *(Winner: Statistical ML — 75-85% recall)*
  7. Agency null spike *(Winner: Statistical ML — 100% recall)*
  8. Closed earlier than created *(Winner: Declarative Rules — 100% recall)*
  9. ZIP inconsistent with borough *(Winner: Declarative Rules — 100% recall)*
  10. Complaint type vs descriptor mismatch *(Winner: Hybrid Statistical + LLM — 100% recall)*
  11. Resolution contradicting status *(Winner: Declarative Rules + LLM — 100% recall)*
  12. Personal data (PII) in free-text *(Winner: Declarative Rules + LLM — 100% recall)*
- **Hybrid Pipeline Breakthrough**: Running an LLM on 100% of rows costs **$180.00 / 1M rows** at 35 rows/s. The **Hybrid Pipeline** runs cheap Declarative Rules and Statistical filters on 100% of rows at line-rate (28,500 rows/s) and routes **< 0.8% suspect rows** to the LLM. This slashes cost to **$1.45 / 1M rows (a 99.2% cost reduction)** with zero loss in recall.

---

## Repository Structure

```
├── run_all.py                  # Master single-command reproduction runner
├── RESULTS_A.md                # Project A benchmarks, Task 5 log, 100k user architecture
├── RESULTS_B.md                # Project B 12-problem matrix, real 2023 issues, 50M scale design
├── DECISION_MATRIX.md          # Unified component decision matrix with measurements
├── AI_USAGE.md                 # Disclosure of AI tools and verification case study
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation and quickstart
├── project_a/
│   ├── models.py               # Pydantic schemas (SalaryInput, TaxBreakdown, ClauseTrace)
│   ├── parser.py               # Plain-language parser & clarification dialog engine
│   ├── official_rules_text/    # Official statutory text (FY 2024-25 & FY 2025-26)
│   ├── hand_coded/             # Hand-coded deterministic rule engine
│   ├── llm_compiled/           # LLM compiler and compiled AST rule files
│   ├── llm_query/              # LLM query-time engine (Gemini Flash)
│   ├── test_suite/             # 212 threshold cases, 30 ITD benchmarks, 50 PL cases, pytest
│   ├── benchmark_a.py          # Project A benchmarking harness
│   └── task5_law_change.py     # Task 5 Finance Act 2025 transition experiment
└── project_b/
    ├── data/                   # Real 2023 NYC 311 cached dataset
    ├── profiler.py             # 2023 raw data quality profiler
    ├── injector.py             # Controlled corruption injector (12 problem types)
    ├── detectors/              # Declarative rules, statistical/ML, and LLM detectors
    ├── hybrid_pipeline.py      # Production 3-stage hybrid firewall
    ├── benchmark_b.py          # Project B 12-problem benchmarking harness
    └── tests/                  # Pytest suite for injector, detectors, and hybrid pipeline
```
