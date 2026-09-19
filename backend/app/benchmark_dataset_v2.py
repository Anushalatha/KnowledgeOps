"""
KnowledgeOps Benchmark Dataset v2 (Expanded 30-Case Multi-Document Suite)

Includes 30 multi-document evaluation cases across 6 technical domain documents:
1. 01_cloud_cost_optimization.pdf
2. 02_cybersecurity_basics.pdf
3. 03_data_engineering_pipeline.pdf
4. 04_product_analytics.pdf
5. 05_networking_fundamentals.pdf
6. 06_machine_learning_evaluation.pdf
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BenchmarkCaseV2(BaseModel):
    id: str
    question: str
    expected_documents: list[str]
    expected_topics: list[str] = Field(default_factory=list)
    category: str  # direct_retrieval, semantic_retrieval, distractor, cross_document, multi_hop, citation_verification, insufficient_evidence
    difficulty: str  # easy, medium, hard
    expected_answer: str | None = None


BENCHMARK_DOCUMENTS_V2 = {
    "01_cloud_cost_optimization.pdf": {
        "title": "Cloud Infrastructure Cost Optimization & FinOps Guide",
        "topic": "Cloud infrastructure, FinOps, rightsizing, auto-scaling, and storage tiering",
        "content": (
            "Cloud Infrastructure Cost Optimization and FinOps Guide. "
            "Rightsizing in cloud infrastructure means matching instance types and sizes to workload capacity and performance requirements at the lowest possible cost. "
            "FinOps practices combine financial management with cloud engineering to provide cost transparency, tag allocation, and budget alerts. "
            "Organizations should leverage auto-scaling policies, spot instances for stateless workloads, and reserved instances or savings plans for predictable baselines. "
            "Storage tiering automatically moves infrequently accessed object data to lower-cost cold or archival storage classes. "
            "Useful operational metrics for cloud cost monitoring include CPU utilization, idle instance ratio, storage growth rate, network egress bandwidth, and monthly cost per active tenant."
        )
    },
    "02_cybersecurity_basics.pdf": {
        "title": "Application Security & Data Protection Standards",
        "topic": "Application security, least privilege, data protection, input validation, and API rate limiting",
        "content": (
            "Application Security and Data Protection Standards. "
            "Application APIs must avoid returning internal implementation details, stack traces, or internal database schemas when an error occurs to prevent information disclosure vulnerabilities. "
            "Principle of Least Privilege dictates that users, applications, and services must be granted only the minimum permissions required to perform their designated tasks. "
            "Input validation and sanitization prevent SQL injection, cross-site scripting (XSS), and command injection attacks. "
            "Security practices for data-processing APIs include mandatory TLS encryption in transit, secret management via dedicated vaults, explicit scope-based OAuth tokens, and rate limiting to prevent denial of service."
        )
    },
    "03_data_engineering_pipeline.pdf": {
        "title": "Data Engineering Ingestion & Pipeline Reliability Architecture",
        "topic": "Data ingestion, idempotency, data contracts, retries, quality checks, and pipeline observability",
        "content": (
            "Data Engineering Ingestion and Pipeline Reliability Architecture. "
            "Idempotency is critical when retrying data processing jobs because an idempotent operation produces the exact same outcome regardless of how many times it is executed with identical input. "
            "A data contract defines the structural schema, data quality rules, SLA expectations, and semantic definitions agreed upon between data producers and data consumers. "
            "Data pipelines rely on automated schema validation, dead-letter queues for unparseable records, atomic batch commits, and exponential backoff retry policies. "
            "Key operational metrics shared between data engineering pipelines and distributed network services include error rate, retry attempt frequency, processing latency, throughput, and dead-letter queue depth."
        )
    },
    "04_product_analytics.pdf": {
        "title": "Product Analytics, Cohort Analysis & Retention Framework",
        "topic": "Product metrics, cohort analysis, user retention, conversion funnels, and experimentation",
        "content": (
            "Product Analytics, Cohort Analysis and Retention Framework. "
            "Cohort analysis breaks users into related groups based on shared characteristics or activation timeframes to analyze behavior and retention patterns over time. "
            "Tracking Daily Active Users (DAU), Monthly Active Users (MAU), and the DAU/MAU stickiness ratio provides visibility into product engagement and habit formation. "
            "Conversion funnel analysis identifies step-by-step drop-off points in user onboarding or purchase checkout flows. "
            "Monitoring helps product analytics teams identify metric anomaly spikes, track feature adoption rates, measure A/B test statistical significance, and evaluate user churn drivers."
        )
    },
    "05_networking_fundamentals.pdf": {
        "title": "Networking Fundamentals & Distributed Systems Reliability",
        "topic": "HTTP protocols, DNS resolution, load balancing, explicit timeouts, circuit breakers, and network resilience",
        "content": (
            "Networking Fundamentals and Distributed Systems Reliability. "
            "DNS (Domain Name System) resolution translates human-readable domain names into IP addresses required for network routing. "
            "Distributed services must use explicit request timeouts to prevent cascading thread pool exhaustion and resource starvation when downstream dependencies slow down. "
            "Circuit breakers monitor downstream failure rates and temporarily trip open to fail fast rather than overloading unhealthy services. "
            "Reliability practices shared between data pipelines and distributed network services include idempotent request handlers, health checks, rate limiting, and exponential backoff with jitter."
        )
    },
    "06_machine_learning_evaluation.pdf": {
        "title": "Machine Learning Model Evaluation & Observability Guide",
        "topic": "Classification metrics, precision, recall, accuracy pitfalls on imbalanced datasets, cross-validation, and drift monitoring",
        "content": (
            "Machine Learning Model Evaluation and Observability Guide. "
            "Accuracy can be misleading for an imbalanced classification problem because a model that always predicts the majority class will achieve high accuracy while failing completely on the minority target class. "
            "Precision measures the proportion of positive predictions that were actually correct, whereas recall measures the proportion of actual positive cases successfully identified. "
            "Machine learning system observability requires monitoring feature data drift, concept drift, prediction distribution shifts, and model latency alongside standard infrastructure metrics. "
            "Cross-validation estimates generalization performance by splitting training data into multiple validation folds."
        )
    }
}

BENCHMARK_CASES_V2: list[dict[str, Any]] = [
    # DIRECT / SEMANTIC (1 - 6)
    {
        "id": "case_01",
        "question": "What does rightsizing mean in cloud infrastructure?",
        "expected_documents": ["01_cloud_cost_optimization.pdf"],
        "expected_topics": ["rightsizing", "capacity", "lowest cost"],
        "category": "direct_retrieval",
        "difficulty": "easy",
        "expected_answer": "Rightsizing in cloud infrastructure means matching instance types and capacity to workload requirements at the lowest possible cost."
    },
    {
        "id": "case_02",
        "question": "Why should application APIs avoid returning internal implementation details when an error occurs?",
        "expected_documents": ["02_cybersecurity_basics.pdf"],
        "expected_topics": ["internal implementation", "error", "information disclosure"],
        "category": "direct_retrieval",
        "difficulty": "easy",
        "expected_answer": "APIs should avoid returning internal implementation details or stack traces to prevent information disclosure vulnerabilities."
    },
    {
        "id": "case_03",
        "question": "Why is idempotency important when retrying data processing jobs?",
        "expected_documents": ["03_data_engineering_pipeline.pdf"],
        "expected_topics": ["idempotency", "retrying", "outcome"],
        "category": "direct_retrieval",
        "difficulty": "medium",
        "expected_answer": "Idempotency ensures that retrying data processing produces identical outcomes without side effects or duplicates."
    },
    {
        "id": "case_04",
        "question": "How does cohort analysis help understand user retention?",
        "expected_documents": ["04_product_analytics.pdf"],
        "expected_topics": ["cohort analysis", "retention", "user behavior"],
        "category": "direct_retrieval",
        "difficulty": "medium",
        "expected_answer": "Cohort analysis groups users by shared traits or activation time to track engagement and retention patterns over time."
    },
    {
        "id": "case_05",
        "question": "Why should distributed services use explicit timeouts?",
        "expected_documents": ["05_networking_fundamentals.pdf"],
        "expected_topics": ["timeouts", "cascading failure", "starvation"],
        "category": "direct_retrieval",
        "difficulty": "easy",
        "expected_answer": "Explicit timeouts prevent cascading failures and resource starvation when downstream dependencies stall."
    },
    {
        "id": "case_06",
        "question": "Why can accuracy be misleading for an imbalanced classification problem?",
        "expected_documents": ["06_machine_learning_evaluation.pdf"],
        "expected_topics": ["accuracy", "imbalanced classification", "majority class"],
        "category": "direct_retrieval",
        "difficulty": "medium",
        "expected_answer": "Accuracy is misleading on imbalanced datasets because predicting only the majority class gives high accuracy while missing minority cases."
    },

    # CROSS-DOCUMENT (7 - 12)
    {
        "id": "case_07",
        "question": "What reliability practices are shared between data pipelines and distributed network services?",
        "expected_documents": ["03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["idempotent", "health checks", "rate limiting", "backoff"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "Shared reliability practices include idempotent operations, health checks, rate limiting, and exponential backoff retry policies."
    },
    {
        "id": "case_08",
        "question": "How does observability differ between an ML system and a data pipeline?",
        "expected_documents": ["06_machine_learning_evaluation.pdf", "03_data_engineering_pipeline.pdf"],
        "expected_topics": ["observability", "concept drift", "schema", "metrics"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "Data pipeline observability focuses on schema contracts, latency, and queue depth, while ML observability adds concept drift and prediction distribution tracking."
    },
    {
        "id": "case_09",
        "question": "What security practices should be applied to APIs that process application data?",
        "expected_documents": ["02_cybersecurity_basics.pdf"],
        "expected_topics": ["TLS encryption", "secret management", "OAuth tokens", "rate limiting"],
        "category": "cross_document",
        "difficulty": "medium",
        "expected_answer": "Security practices include TLS encryption, secret vaults, scope-based OAuth tokens, input validation, and rate limiting."
    },
    {
        "id": "case_10",
        "question": "How can retry strategies affect both data processing and distributed services?",
        "expected_documents": ["03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["retry strategies", "backoff", "idempotency"],
        "category": "cross_document",
        "difficulty": "medium",
        "expected_answer": "Exponential backoff retries with idempotency prevent duplicate processing in pipelines and reduce load on degraded network services."
    },
    {
        "id": "case_11",
        "question": "What operational metrics are useful for both cloud infrastructure and data pipelines?",
        "expected_documents": ["01_cloud_cost_optimization.pdf", "03_data_engineering_pipeline.pdf"],
        "expected_topics": ["operational metrics", "latency", "error rate", "bandwidth"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "Useful shared metrics include error rates, processing latency, throughput, resource utilization, and storage growth rates."
    },
    {
        "id": "case_12",
        "question": "How can monitoring help identify problems in both ML systems and product analytics?",
        "expected_documents": ["06_machine_learning_evaluation.pdf", "04_product_analytics.pdf"],
        "expected_topics": ["monitoring", "drift", "anomaly spikes", "conversion"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "Monitoring detects prediction distribution shifts in ML systems and anomaly metric spikes or churn drivers in product analytics."
    },

    # MULTI-HOP (13 - 15)
    {
        "id": "case_13",
        "question": "A service processes analytical data through an API. What practices should be used to protect the API, make the pipeline retry-safe, and monitor failures?",
        "expected_documents": ["02_cybersecurity_basics.pdf", "03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["protect the API", "retry-safe", "monitor failures"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Use TLS and rate limiting for API protection, idempotent handlers with exponential backoff for retries, and explicit timeouts with dead-letter queue metrics."
    },
    {
        "id": "case_14",
        "question": "A machine learning service is deployed in a distributed environment. What should be monitored and what network reliability mechanisms should be considered?",
        "expected_documents": ["06_machine_learning_evaluation.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["concept drift", "timeouts", "circuit breakers"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Monitor data/concept drift and prediction latency while implementing circuit breakers and explicit request timeouts."
    },
    {
        "id": "case_15",
        "question": "A company wants to reduce cloud spending without damaging service reliability. What principles should guide the optimization?",
        "expected_documents": ["01_cloud_cost_optimization.pdf"],
        "expected_topics": ["rightsizing", "reserved instances", "auto-scaling"],
        "category": "multi_hop",
        "difficulty": "medium",
        "expected_answer": "Principles include workload rightsizing, reserved instances for predictable baselines, spot instances for stateless tasks, and auto-scaling."
    },

    # DISTRACTOR TESTS (16 - 20)
    {
        "id": "case_16",
        "question": "What is cohort analysis?",
        "expected_documents": ["04_product_analytics.pdf"],
        "expected_topics": ["cohort analysis", "retention"],
        "category": "distractor",
        "difficulty": "easy",
        "expected_answer": "Cohort analysis divides users into groups based on shared characteristics to study behavior over time."
    },
    {
        "id": "case_17",
        "question": "What is DNS used for?",
        "expected_documents": ["05_networking_fundamentals.pdf"],
        "expected_topics": ["DNS", "IP addresses"],
        "category": "distractor",
        "difficulty": "easy",
        "expected_answer": "DNS translates human-readable domain names into IP addresses for network routing."
    },
    {
        "id": "case_18",
        "question": "What is precision in classification?",
        "expected_documents": ["06_machine_learning_evaluation.pdf"],
        "expected_topics": ["precision", "positive predictions"],
        "category": "distractor",
        "difficulty": "easy",
        "expected_answer": "Precision measures the proportion of positive predictions that were actually correct."
    },
    {
        "id": "case_19",
        "question": "What is a data contract?",
        "expected_documents": ["03_data_engineering_pipeline.pdf"],
        "expected_topics": ["data contract", "schema"],
        "category": "distractor",
        "difficulty": "easy",
        "expected_answer": "A data contract defines structural schema, SLAs, and data quality rules between data producers and consumers."
    },
    {
        "id": "case_20",
        "question": "What is least privilege?",
        "expected_documents": ["02_cybersecurity_basics.pdf"],
        "expected_topics": ["least privilege", "minimum permissions"],
        "category": "distractor",
        "difficulty": "easy",
        "expected_answer": "Least privilege grants users or services only the minimum necessary permissions to perform their tasks."
    },

    # ADDITIONAL DIFFICULT MULTI-HOP & CROSS-DOCUMENT CASES (21 - 30)
    {
        "id": "case_21",
        "question": "How can network circuit breakers and pipeline dead-letter queues be combined to handle persistent external API outages?",
        "expected_documents": ["03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["circuit breakers", "dead-letter queues", "outages"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Circuit breakers trip open to stop overloading unhealthy dependencies, while dead-letter queues store unparseable or failed records for asynchronous retry."
    },
    {
        "id": "case_22",
        "question": "A company wants to optimize cloud infrastructure costs while preventing API rate-limiting and security exposure. What strategies should be implemented?",
        "expected_documents": ["01_cloud_cost_optimization.pdf", "02_cybersecurity_basics.pdf"],
        "expected_topics": ["cost optimization", "rate limiting", "security"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Implement rightsizing and auto-scaling for cost efficiency alongside scope-based OAuth tokens, TLS, and API rate limiting for security."
    },
    {
        "id": "case_23",
        "question": "How do product retention metrics (like DAU/MAU) inform machine learning model monitoring for feature drift?",
        "expected_documents": ["04_product_analytics.pdf", "06_machine_learning_evaluation.pdf"],
        "expected_topics": ["DAU/MAU", "concept drift", "feature drift"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "Product analytics stickiness metrics (DAU/MAU) reveal user behavior shifts that signal feature data drift or concept drift in machine learning models."
    },
    {
        "id": "case_24",
        "question": "What practices protect an analytical pipeline against schema drift, unauthorized access, and network starvation?",
        "expected_documents": ["02_cybersecurity_basics.pdf", "03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["schema drift", "unauthorized access", "network starvation"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Enforce data contracts for schema validation, OAuth tokens and TLS for access control, and explicit request timeouts with circuit breakers against starvation."
    },
    {
        "id": "case_25",
        "question": "How does input sanitization in web security differ from data contract schema validation in ETL pipelines?",
        "expected_documents": ["02_cybersecurity_basics.pdf", "03_data_engineering_pipeline.pdf"],
        "expected_topics": ["input sanitization", "data contract", "schema validation"],
        "category": "cross_document",
        "difficulty": "medium",
        "expected_answer": "Input sanitization prevents injection attacks like SQLi/XSS, whereas data contracts enforce structural schemas and SLA agreements between data producers and consumers."
    },
    {
        "id": "case_26",
        "question": "What cloud storage tiering policies should be applied to cold dead-letter queue records?",
        "expected_documents": ["01_cloud_cost_optimization.pdf", "03_data_engineering_pipeline.pdf"],
        "expected_topics": ["storage tiering", "dead-letter queues"],
        "category": "cross_document",
        "difficulty": "medium",
        "expected_answer": "Move dead-letter queue records to lower-cost cold or archival storage classes after initial investigation to optimize cloud costs."
    },
    {
        "id": "case_27",
        "question": "Why is cross-validation insufficient for detecting concept drift in production ML models?",
        "expected_documents": ["06_machine_learning_evaluation.pdf"],
        "expected_topics": ["cross-validation", "concept drift", "production"],
        "category": "distractor",
        "difficulty": "medium",
        "expected_answer": "Cross-validation evaluates historical training data generalization but cannot detect real-time feature data drift or concept drift in production distributions."
    },
    {
        "id": "case_28",
        "question": "What shared operational metrics should be monitored to detect both networking bottleneck timeouts and data ingestion queue lag?",
        "expected_documents": ["03_data_engineering_pipeline.pdf", "05_networking_fundamentals.pdf"],
        "expected_topics": ["operational metrics", "latency", "queue depth", "error rate"],
        "category": "multi_hop",
        "difficulty": "hard",
        "expected_answer": "Shared metrics include processing latency, request error rates, throughput, and queue depth."
    },
    {
        "id": "case_29",
        "question": "How can A/B experimentation funnels be used to validate cloud auto-scaling cost savings?",
        "expected_documents": ["01_cloud_cost_optimization.pdf", "04_product_analytics.pdf"],
        "expected_topics": ["experimentation", "auto-scaling", "cost savings"],
        "category": "cross_document",
        "difficulty": "hard",
        "expected_answer": "A/B experimentation frameworks evaluate statistical significance of feature changes while tracking infrastructure CPU utilization and monthly cost per active tenant."
    },
    {
        "id": "case_30",
        "question": "What quantum encryption algorithm is used by KnowledgeOps for satellite network communication?",
        "expected_documents": [],
        "expected_topics": [],
        "category": "insufficient_evidence",
        "difficulty": "hard",
        "expected_answer": "I don't have enough information in the provided knowledge base to answer this."
    }
]
