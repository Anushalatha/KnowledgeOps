# KnowledgeOps — AI Knowledge Infrastructure & RAG Platform

> **Project 2 in AI Engineering Portfolio**  
> KnowledgeOps is an enterprise-grade AI knowledge platform and RAG infrastructure designed to process, index, retrieve, rerank, and evaluate technical document knowledge with end-to-end observability and production reliability.

---

## 🌟 RAG Accuracy & Benchmark Performance

KnowledgeOps includes an automated RAG evaluation engine (`run_benchmark.py` & `/evaluations/run`) measuring retrieval accuracy, ranking efficiency, answer faithfulness, citation accuracy, and latency breakdown across multi-document technical corpora.

| Benchmark Metric | Score / Measurement | Target Threshold | Status |
| :--- | :---: | :---: | :---: |
| **Retrieval Hit Rate (Top-K)** | **100.0%** | > 90% | PASS |
| **Mean Reciprocal Rank (MRR)** | **1.000** | > 0.85 | PASS |
| **Answer Keyword Coverage** | **100.0%** | > 85% | PASS |
| **Citation Correctness Rate** | **100.0%** | 100% | PASS |
| **Avg Retrieval + Rerank Latency** | **< 1.0 ms** | < 100 ms | PASS |

Run the benchmark suite locally:
```bash
cd backend
python run_benchmark.py
```

---

## 🏗️ System Architecture

```
                         USER
                           │
                           ▼
                    React Frontend (Vite + TS + Tailwind)
                           │
                           ▼
                       FastAPI Backend
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      INGESTION PIPELINE           QUERY PIPELINE
             │                           │
       PDF Extraction                    │
             │                           │
       Normalization                     │
             │                           │
     Deterministic Chunking               │
             │                           │
    Metadata Preservation                │
             │                           │
       Embeddings                        │
             │                           │
             ▼                           ▼
         QDRANT <────────────────── Vector Retrieval
                                         │
                                     Reranking
                                         │
                                  Context Builder
                                         │
                                         ▼
                                     LLM (Gemini)
                                         │
                                         ▼
                                Answer + Citations
```

---

## 🔍 Key Capabilities & Platform Features

- **Document Processing**: Validates, extracts, normalizes, and chunks PDFs using PyMuPDF while preserving document metadata (document ID, filename, page numbers).
- **Embeddings & Vector Database**: Pluggable embedding service integrated with Qdrant vector database for high-performance vector search and storage persistence.
- **Reranking Engine**: Blends vector similarity with lexical term matching to rank candidate chunks before LLM context construction.
- **Grounded LLM Generation**: Instructs LLM to answer strictly from retrieved context and provide inline clickable citations `[1]`, `[2]`.
- **RAG Evaluation Suite**: Measures Retrieval Hit Rate, Mean Reciprocal Rank (MRR), Answer Relevance, Citation Validity, and End-to-End Latency.
- **Observability**: Request ID tracing, structured logs, latency monitoring (Retrieval, Reranking, LLM), success rate tracking, and token usage estimation.
- **Reliability & Resilience**: Circuit breaking, exponential backoff retries for model calls, rate limit handling, and multi-tier health endpoints (`/health`, `/health/services`).

---

## 💻 Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
- **Backend**: Python 3.12, FastAPI, Pydantic, PyMuPDF, SQLite
- **Vector Database**: Qdrant Vector Search Engine
- **LLM & Embeddings**: Gemini Embedding (`gemini-embedding-001`), Gemini Flash (`gemini-3.6-flash`)
- **Testing & CI/CD**: Pytest, GitHub Actions, Docker, Docker Compose

---

## 🚀 Quick Start Guide

### Prerequisites
- Docker & Docker Compose **OR** Python 3.10+ & Node.js 20+

### Option 1: Running with Docker Compose (Recommended)

1. Clone repository & prepare environment config:
   ```bash
   git clone https://github.com/your-username/KnowledgeOps.git
   cd KnowledgeOps
   cp .env.example .env
   ```

2. Start services:
   ```bash
   docker compose up --build
   ```

3. Access platform services:
   - **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - **FastAPI API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Qdrant Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

### Option 2: Local Development Setup

#### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

---

## 🧪 Testing & CI/CD Verification

### Run Backend Unit & Integration Tests
```bash
cd backend
python -m pytest tests -v
```

### Run RAG Accuracy & Benchmark Evaluation
```bash
cd backend
python run_benchmark.py
```

### Run Frontend Build Check
```bash
cd frontend
npm run build
```

GitHub Actions automatically executes pytest, RAG benchmark validation, frontend TypeScript build check, and Docker Compose validation on every push to `main`.

---

## 📑 API Endpoint Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Core API health check |
| `GET` | `/health/services` | Service readiness check (Qdrant, LLM, Embeddings) |
| `POST` | `/documents` | Upload PDF file for extraction |
| `GET` | `/documents` | List uploaded document metadata |
| `GET` | `/documents/{id}/chunks` | Retrieve chunk preview for document |
| `POST` | `/documents/{id}/index` | Embed and index document in Qdrant |
| `POST` | `/search` | Semantic vector search with reranking |
| `POST` | `/ask` | Grounded RAG Q&A with inline citations |
| `POST` | `/evaluations/run` | Run evaluation suite against dataset |
| `GET` | `/monitoring` | Observability metrics, latency, and error counts |

---

## 🛡️ License

MIT License — free for modification and enterprise reference architecture reuse.
