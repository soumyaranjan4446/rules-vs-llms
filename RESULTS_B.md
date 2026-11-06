# RESULTS_B.md — Project B: Data-Quality Checks for NYC 311 & Enterprise Dashboards

**Candidate:** Soumya Ranjan Patra  
**Hiring Organization:** Fire AI  
**Assignment:** Rules vs LLMs Take-Home Assignment  
**Domain:** NYC 311 Service Requests Data-Quality Pipeline & Dashboard Firewall

---

## 1. Real Quality Deficiencies Discovered in 2023 NYC 311 Data

We profiled 4,500 real service requests created during calendar year 2023 downloaded directly from the official **NYC Open Data Socrata API** (`erm2-nwe9`). The data contains significant intrinsic data-quality anomalies:

| Quality Issue Category | Occurrences Found in 2023 Sample | Percentage of Sample | Concrete Real-World Examples from 2023 Raw Data |
| :--- | :---: | :---: | :--- |
| **Closed Date Earlier Than Created Date** | **9** | **0.20%** | • `unique_key: 59135314` (Agency: DOT)<br>&nbsp;&nbsp;`created_date`: 2023-10-16T10:54:00<br>&nbsp;&nbsp;`closed_date`: 2023-10-13T10:53:00 (Closed 3 days before creation!)<br>• `unique_key: 59129567` (Agency: DOT)<br>&nbsp;&nbsp;`created_date`: 2023-10-16T10:53:00, `closed_date`: 2023-10-13T10:53:00 |
| **PII Leakage in Free-Text Fields** | **179** | **3.98%** | • `unique_key: 57333089` (Agency: DEP)<br>&nbsp;&nbsp;Resolution text contains raw citizen contact telephone: `212-639-9675`<br>• `unique_key: 57330531` (Agency: DOB)<br>&nbsp;&nbsp;Resolution contains phone number `212-639-9675` in unredacted comment |
| **Missing Critical Geographic Coordinates** | **62** | **1.38%** | • Records with null `latitude` and null `longitude`, preventing geospatial aggregation on municipal dashboard maps |
| **Missing Incident ZIP Codes** | **43** | **0.96%** | • Tickets missing postal codes despite containing valid street addresses, skewing borough-level CFO financial allocations |
| **Unspecified Borough Designation** | **2** | **0.04%** | • `unique_key: 58204564` (Ferry Inquiry) and `58204560` (Vehicle Complaint) marked with `borough == "Unspecified"` |
| **Missing Resolution Descriptions** | **17** | **0.38%** | • Closed tickets with null resolution details |

---

## 2. 12-Problem Detection, False-Alarm and Cost Evaluation Matrix

Using our controlled **Corruption Injector**, we injected each of the 12 specified problem types into clean batches at an 8% injection rate, and evaluated detection performance across:
1. **Declarative Rules / Schema Checks**
2. **Statistical / ML Detectors**
3. **LLM Review (Gemini 1.5 Flash)**
4. **Hybrid Multi-Stage Pipeline**

### Problem Detection Recall Table

| Problem Type | Declarative Rules | Statistical / ML | LLM Review | Hybrid Pipeline | Optimal Winning Detector |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **a. Renamed or dropped column** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **b. Column type change (numbers as strings)** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **c. Date format switch partway through batch** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **d. Latitude and longitude swapped** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **e. Exact duplicates** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **f. Near-duplicates (altered timestamp/text)** | 0.0% | **75.0%** | 0.0% | **75.0%** | `Statistical / ML` |
| **g. Null spike in one agency's records** | 0.0% | **100.0%** | 0.0% | **100.0%** | `Statistical / ML` |
| **h. Closed date earlier than created date** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **i. ZIP code inconsistent with borough** | **100.0%** | 0.0% | 0.0% | **100.0%** | `Declarative Rules` |
| **j. Complaint Type inconsistent with Descriptor** | 0.0% | **100.0%** | **100.0%** | **100.0%** | `Statistical / ML + LLM` |
| **k. Resolution Description contradicting Status** | **100.0%** | 0.0% | **100.0%** | **100.0%** | `Declarative Rules` |
| **l. Personal data (PII) inside free-text** | **100.0%** | 0.0% | **100.0%** | **100.0%** | `Declarative Rules + LLM` |

---

### Detector Family Cost, Throughput & False-Alarm Benchmark

| Detector Family | False-Alarm Rate on Clean Batch | Cost per Million Rows ($) | Laptop Throughput (rows/sec) | Alert Clarity & Interpretability |
| :--- | :---: | :---: | :---: | :--- |
| **Declarative Rules** | **5.7%** | **$0.00** | **125,000 rows/s** | **High**: Cites exact statutory field, failing schema constraint, or invalid range. |
| **Statistical / ML** | **6.6%** | **$0.00** | **38,000 rows/s** | **Medium-High**: Provides Z-score deviation, baseline rate, and Jaccard similarity metrics. |
| **LLM Review (100% rows)** | **5.0%** | **$180.00** | **35 rows/s** | **Very High**: Generates natural-language reasoning of semantic contradictions. |
| **Hybrid Pipeline** | **10.3%** | **$1.45** | **28,500 rows/s** | **High to Very High**: Multi-stage attribution combining rule precision with LLM verification. |

### Analysis of Trade-offs:
1. **The Cost of Over-using AI**: Running LLM review across 100% of rows costs **$180.00 per million rows** and drops laptop throughput to an unviable **35 rows/sec**. At enterprise scale (50M rows/day), this translates to **$9,000/day ($3.28 Million/year)** just for data validation!
2. **The Power of the Hybrid Pipeline**: The Hybrid Pipeline runs cheap Declarative Rules and Statistical checks first at line-rate. It routes **less than 0.8% of suspect rows** to the LLM for deep semantic audit. This slashes the cost from **$180.00 down to $1.45 per million rows** (a **99.2% cost reduction**) while maintaining **100% detection recall** on semantic contradictions!

---

## 3. Scale and Enterprise Design: 50 Million Rows/Day Across 120 Customers

### System Architecture Diagram (50M Rows / Day)

```mermaid
flowchart TD
    subgraph Ingestion["Ingestion Layer (120 Enterprise Tenants)"]
        Kafka["Distributed Apache Kafka / Redpanda Cluster\n(120 Tenant Topics, Partitioned by Customer ID)"]
    end

    subgraph Stage1["Stage 1: Streaming Declarative Firewall (100% of Rows)"]
        Flink["Apache Flink / Rust Engine\n• Schema Registry & Type Validation\n• Geo-fence Bounds (NYC Polygon)\n• Temporal Ordering Check\n• Fast Regex PII Redaction"]
    end

    subgraph Stage2["Stage 2: Micro-Batch Statistical Engine (Windowed)"]
        Spark["Windowed Streaming Engine\n• Rolling Null-Rate Z-Scores per Agency/Tenant\n• Locality Sensitive Hashing (LSH) for Near-Duplicates\n• Distribution Drift Monitoring"]
    end

    subgraph Routing{"Anomaly Filter & Triage"}
        Pass["Valid Clean Rows (99%+)"] --> DashboardDB["ClickHouse / Snowflake\nClean Analytics Warehouse\n(Powering CFO Dashboards)"]
        HardError["Structural Schema / Format Failure"] --> DeadLetter["Dead Letter Queue (DLQ)\n(Automated Alert to Source ERP)"]
        SemanticAmbiguity["Semantic Discrepancy\n(Category vs Descriptor Mismatch)"] --> Stage3["Stage 3: Targeted LLM Pool\n(0.5% - 1.0% Suspect Rows)"]
    end

    subgraph Stage3_LLM["Stage 3: Asynchronous LLM Review"]
        Stage3 --> LLMPool["Batched vLLM / Gemini Flash Pool\n• Semantic Contradiction Audit\n• Edge-Case PII Redaction"]
        LLMPool --> VerifiedAlert["Verified Actionable Anomaly Alert\n(PagerDuty / Slack / Dashboard Warning)"]
    end

    Kafka --> Flink
    Flink --> Spark
    Spark --> Routing
```

### Projections for 50 Million Rows / Day:
- **Daily Volume**: 50,000,000 rows/day = ~578 rows/second average (bursts up to 3,500 rows/sec).
- **Latency SLAs**:
  - P50 Stream Latency (Ingest to Dashboard): **< 250 milliseconds**.
  - P99 Alert Latency: **< 1.5 seconds**.
- **Financial Cost Modeling**:
  - **Stage 1 (Declarative on Flink/Rust)**: $0.00 LLM cost. Compute infrastructure: 3 nodes (c6i.2xlarge) = **$18.50 / day**.
  - **Stage 2 (Statistical Spark/Flink Windows)**: $0.00 LLM cost. Compute infrastructure: 4 nodes = **$24.00 / day**.
  - **Stage 3 (Targeted LLM Review on 0.5% rows = 250,000 rows/day)**: 250,000 calls $\times$ $0.00018 = **$45.00 / day**.
  - **Total Cost**: **~$87.50 / day** ($2,625 / month) for 50 Million rows/day across 120 tenants.
  - *Contrast with Naive Query-Time LLM*: 50M calls/day = **$9,000 / day ($270,000 / month)**! The hybrid design delivers a **99.0% cost savings**.

---

### Which Choices Would Change at That Scale, and Why?

1. **Schema Polymorphism via Schema Registry Instead of Hardcoded Dictionaries**:
   - *Why*: Across 120 customers with different schemas (e.g. some using SAP, some Salesforce, some NYC 311 formats), schema definitions cannot live in static Python files. We replace local Python sets with an **Apache Kafka Schema Registry (Protobuf/Avro)** that dynamically enforces tenant-specific contract validation.
2. **Locality Sensitive Hashing (LSH) / MinHash Replaces Pairwise Comparisons**:
   - *Why*: In a batch of 1,000 rows on a laptop, pairwise comparisons ($O(N^2)$) take a few milliseconds. At 50 million rows/day, $O(N^2)$ comparisons require $2.5 \times 10^{15}$ operations, which would grind the cluster to a halt. LSH buckets records into sub-linear hash buckets ($O(N)$) to detect near-duplicates in sub-seconds.
3. **Local Self-Hosted Small Language Models (SLMs) Replace External SaaS API Calls**:
   - *Why*: Sending 250,000 customer rows outside the VPC to external public APIs introduces data privacy compliance risks (SOC2, GDPR, HIPAA). At 50M rows/day, we deploy dedicated quantized local SLMs (e.g., Llama-3-8B-Instruct or Qwen-2.5-7B via vLLM on 2x L4 GPUs) inside the private tenant VPC. This caps marginal costs to fixed GPU compute hours with zero per-token billing.
4. **Asynchronous Non-Blocking LLM Triage (Out-of-Band)**:
   - *Why*: High-throughput CFO dashboards cannot tolerate synchronous 800ms HTTP blocking calls in the critical ingest path. The pipeline writes all structurally clean data immediately into ClickHouse for instant querying, while semantic LLM audits run out-of-band in a parallel worker pool, appending confidence flags asynchronously.
