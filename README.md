# Instamart Customer Intelligence & Automated Operations Capstone
An end-to-end data pipeline, customer segmentation model, LLM ticket classification system, and autonomous policy-grounded RAG agent built using Python and the standard library, SQLite, Pandas, Scikit-Learn, and a mock LLM interface.

---

## Overview

The **Instamart Customer Intelligence** project solves four core retail analytics and automation challenges:
1. **Data Cleaning & Engineering (Part A):** Auditing raw CSV data, handling corrupt records, parsing messy timestamps, imputing missing values, and persisting a clean SQLite database (`instamart.db`).
2. **Customer Segmentation & Churn Modeling (Part B):** Building an RFM (Recency, Frequency, Monetary) feature store, running K-Means clustering, and training a Random Forest model to predict customer churn.
3. **Automated Support Triage (Part C):** Processing customer support tickets through safety input guardrails, PII redaction, few-shot LLM classification, fallback/retry mechanisms, and routing.
4. **Policy-Grounded RAG & Autonomous Agent (Part D):** Implementing a chunked TF-IDF vector retrieval system against company policy documents, integrating SQLite order tools, and operating a ReAct agent to handle automated refunds and escalations.

---

## Reproduce

To run the entire end-to-end pipeline from scratch:

1. **Generate Synthetic Data:**
   ```bash
   python generate_data.py

```

2. **Execute Part A (Data Cleaning & Audit):**
```bash
python part_a.py

```


3. **Execute Part B (RFM Clustering & Churn Model):**
```bash
python part_b.py

```


4. **Execute Part C (Triage & Routing Pipeline):**
```bash
python part_c.py

```

5. **Execute Part D (Policy RAG & Autonomous Agent):**
```bash
python pard_d.py

```
---

## Part A: Data Audit, Cleaning, and SQLite Loading

Raw data ingest uncovered several anomalies that were cleaned programmatically:

* **Orders Shape:** $(13,084, 9)$ rows $\times$ columns
* **Exact Duplicates:** $119$ rows removed
* **Pending Status Rows:** $656$ rows
* **Distinct Order IDs:** $12,309$ valid unique transactions
* **Total Completed Spend (Revenue Check):** **INR 2,998,668.80**

### SQL Analytics Queries (`sql/queries.sql`)

* **Q1:** High-value customers spending over INR 8,000 across orders valued $> \text{INR } 500$.
* **Q2:** Total revenue aggregated by City and Product Category.
* **Q3:** Premium products priced above the catalog average.
* **Q4:** Inactive customers with zero completed orders.
* **Q5:** Customers whose total spend exceeds the overall average customer spend.
* **Q6:** City-level customer revenue ranking using window functions (`RANK()`, `DENSE_RANK()`, `ROW_NUMBER()`).
* **Q7:** Daily revenue and cumulative running total revenue.

---

## Part B: Customer Segmentation & Churn Modeling

* **K-Means Clustering ($K=4$):** Segmented customers into *High-Value VIP*, *Frequent Shoppers*, *Occasional Buyers*, and *At-Risk Lapsed*.
* **Churn Target Setup:** Defined a cutoff of `2025-09-01` to predict September 2025 activity.
* **Random Forest Model:** Trained using numerical features (recency, frequency, monetary, average discount, delivery time, cancellation rate, tenure) and encoded categorical features (`city`, `gender`, `fav_category`).
* **Artifacts Saved:**
* Segments exported to `outputs/customer_segments.csv`
* Model pipeline persisted via Joblib at `outputs/lapse_model.joblib`
* Prioritized premium retention targets exported to `outputs/retention_list.csv`

---

## Part C: AI Support Ticket Triage & Routing

Processed incoming support tickets via a robust production loop:

1. **Input Guardrails:** Skipped empty tickets and flagged over-length texts ($\gt 400$ estimated tokens) for human review.
2. **PII Redaction:** Automatically masked email addresses, 10-digit phone numbers, and order IDs (`ORD-XXXXXX`).
3. **LLM Classification:** Used a resilient few-shot prompt with automatic exponential backoff retry handling for transient LLM errors (simulated 503 server busy).
4. **Validation:** Ensured strict JSON formatting or fallback keyword parsing.
5. **Routing Rules:**
* Fraud tickets $\rightarrow$ `security_team` (**HIGH** priority)
* Premium customer issues $\rightarrow$ `premium_desk` (**HIGH** priority)
* Standard issues $\rightarrow$ `support_queue` (**NORMAL** priority)
* Invalid/malformed outputs $\rightarrow$ `human_review` (**NORMAL** priority)

Outputs saved to `outputs/triage_results.csv` and demo budget subset at `outputs/triage_budget_demo.csv`.

---

## Part D: RAG & Autonomous Agent Operations

* **Chunked Policy Retrieval:** Policy documents (`refund_policy.txt`, `delivery_policy.txt`, `payment_policy.txt`, `privacy_policy.txt`, `escalation_policy.txt`) are chunked (chunk size = 40 words, overlap = 10 words) and indexed using a TF-IDF vectorizer for cosine similarity search.
* **Tool Set Integration:**
* `get_order(order_id)`: Queries SQLite for order status, amount, and delivery time.
* `search_policy(query)`: Retrieves relevant policy clauses via RAG.
* `calculate_refund(order_amount, delivery_minutes)`: Applies rule engine (full refund if completed and delivery $\gt 45$ minutes).
* `issue_refund(order_id, refund_inr)` / `escalate_to_human(order_id, refund_inr)`: Executes transactions and logs events to `outputs/refund_ledger.jsonl`.


* **Execution Logs:** Agent trace steps, token consumption, and state recovery checkpoints are saved under `state/` and `outputs/agent_runs.jsonl`.

---

## Limitations and Next Steps

### Limitations

* **TF-IDF Retrieval:** Keyword-based matching may miss semantic intent for complex or paraphrased customer inquiries compared to dense neural embeddings.
* **Mock LLM Constraints:** The offline mock LLM simulates predetermined classification and ReAct behaviors, limiting dynamic creative reasoning on out-of-distribution queries.
* **Static Snapshot:** Models rely on fixed temporal cutoffs (`2025-10-01`) and require scheduled batch re-training to adapt to shifting user behavior.

### Next Steps

1. **Neural Embeddings:** Upgrade the policy RAG engine to utilize vector embeddings and a dedicated vector database (e.g., ChromaDB or FAISS).
2. **Live LLM Integration:** Transition from the mock interface to production APIs (like OpenAI or Gemini SDK) with fine-tuned function calling schemas.
3. **Real-Time Monitoring:** Implement automated drift detection on customer segmentation features and build a real-time alerting dashboard for high-risk churn cohorts.

```

<FollowUp label="Want me to help you format this into a script that automatically writes README.md?" query="Write a python script to automatically generate the README.md file with this exact content."/>

```
*   `california_housing_data*.csv` is California housing data from the 1990 US
    Census; more information is available at:
    https://docs.google.com/document/d/e/2PACX-1vRhYtsvc5eOR2FWNCwaBiKL6suIOrxJig8LcSBbmCbyYsayia_DvPOOBlXZ4CAlQ5nlDD8kTaIDRwrN/pub

*   `mnist_*.csv` is a small sample of the
    [MNIST database](https://en.wikipedia.org/wiki/MNIST_database), which is
    described at: http://yann.lecun.com/exdb/mnist/

*   `anscombe.json` contains a copy of
    [Anscombe's quartet](https://en.wikipedia.org/wiki/Anscombe%27s_quartet); it
    was originally described in

    Anscombe, F. J. (1973). 'Graphs in Statistical Analysis'. American
    Statistician. 27 (1): 17-21. JSTOR 2682899.

    and our copy was prepared by the
    [vega_datasets library](https://github.com/altair-viz/vega_datasets/blob/4f67bdaad10f45e3549984e17e1b3088c731503d/vega_datasets/_data/anscombe.json).
