# KnowledgeOps — AI Knowledge Infrastructure & RAG Platform

> **Project 2 in AI Engineering Portfolio**  
> KnowledgeOps is an enterprise-grade AI knowledge platform and RAG infrastructure designed to process, index, retrieve, rerank, and evaluate technical document knowledge with end-to-end observability, MMR retrieval diversity, and production reliability.

---

## 🖼️ Platform Visual Interface & Screenshots

### 1. Quality Engineering & RAG Evaluation Suite
![KnowledgeOps RAG Evaluation Suite](docs/screenshots/dashboard.png)

### 2. Document Ingestion, Processing & Indexing
![Document Ingestion & Management](docs/screenshots/documents.png)

### 3. Vector Search & Reranking Inspection
![Semantic Vector Search](docs/screenshots/search.png)

### 4. Grounded RAG Q&A with Citation Verification
![Grounded RAG Q&A](docs/screenshots/Query.png)

---

## 📊 RAG Benchmark Dataset v2 Results (30 Cases across 6 Technical Domains)

KnowledgeOps features a multi-document quality engineering evaluation engine (`backend/run_benchmark.py` & `/evaluations/benchmark/run`). It assesses retrieval accuracy, ranking efficiency, MMR context diversity, answer relevance, citation validity, and latency breakdown.

### 1. Before vs. After Optimization Performance (Top-K = 5)

| Metric | Before Optimization | After Optimization | Net Change / Status |
| :--- | :---: | :---: | :---: |
| **Retrieval Hit Rate** | 100.0% | **100.0%** | Maintained 100% (PASS) |
| **Mean Reciprocal Rank (MRR)** | 0.925 | **0.950** | **+0.025** (PASS) |
| **Recall @ 5** | 100.0% | **100.0%** | Maintained 100% (PASS) |
| **Precision @ 5** | 28.0% | **34.0%** | **+6.0% (Reduced Redundancy)** |
| **Answer Relevance** | 41.4% | **71.1%** | **+29.7% (Aspect-Aware Generation)** |
| **Groundedness** | 100.0% | **100.0%** | **100% Faithful (PASS)** |
| **Citation Correctness** | 90.0% | **100.0%** | **+10.0% (PASS)** |
| **Average Total Latency** | 2.9 ms | **4.7 ms** | **+1.8 ms (Sub-10ms Engine)** |

---

### 2. Multi-MMR Configuration Comparison (Top-K = 5)

| Configuration | Hit Rate | MRR | Precision@5 | Recall@5 | Answer Relevance | Citation Correctness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **MMR OFF** | 100.0% | 0.950 | 34.0% | 100.0% | 71.1% | 100.0% |
| **MMR ON (λ = 0.50)** | 100.0% | 0.950 | 34.0% | 100.0% | 71.1% | 100.0% |
| **MMR ON (λ = 0.70)** | 100.0% | 0.950 | 34.0% | 100.0% | 71.1% | 100.0% |
| **MMR ON (λ = 0.90)** | 100.0% | 0.950 | 34.0% | 100.0% | 71.1% | 100.0% |

---

### 3. Top-K Performance Matrix (MMR Enabled, λ = 0.70)

| Top K | Hit Rate | MRR | Recall@K | Answer Relevance | Citation Correctness | Avg Latency |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **K = 3** | 100.0% | 0.950 | 95.6% | 71.1% | 100.0% | 4.5 ms |
| **K = 5** | 100.0% | 0.950 | 100.0% | 71.1% | 100.0% | 4.7 ms |
| **K = 10** | 100.0% | 0.950 | 100.0% | 71.1% | 100.0% | 4.8 ms |

---

## 🏗️ System Architecture

```
                                USER / CLIENT
                                      │
                                      ▼
                      React 18 Dashboard (TypeScript + Vite)
                                      │
                                      ▼
                          FastAPI Backend Gateway
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
     INGESTION PIPELINE                              QUERY PIPELINE
              │                                               │
     PDF File Upload & Validation                      User Question
              │                                               │
     Text Extraction (PyMuPDF)                         Query Vectorization
              │                                               │
    Deterministic Chunking                             Vector Search (Qdrant)
    & Metadata Tagging                                        │
              │                                       MMR Diversity Reranking
     Vector Embedding                                  (λ=0.70, Pool=15)
              │                                               │
              ▼                                       Structured Context Builder
       QDRANT VECTOR DB <──────────────────────────────┤
                                                              │
                                                      Answer Planner
                                                      (Aspect Decomposition)
                                                              │
                                                      LLM Generation (Gemini)
                                                              │
                                                      Citation Validator
                                                              │
                                                      Evaluator Engine
                                                      (Relevance, Groundedness, Citations)
```

---

## 🔍 Key Capabilities & Technical Features

- **Document Processing**: Validates, extracts, normalizes, and chunks PDFs using PyMuPDF while preserving document metadata (document ID, filename, chunk ID, page numbers).
- **Maximal Marginal Relevance (MMR) Reranking**: Blends vector similarity with lexical term matching and applies an intra-document penalty ($0.40$) to prevent single-document clutter.
- **Structured Context Construction**: Formats retrieved chunks into explicit metadata blocks (`[1] Document, Chunk ID, Score, Content`).
- **Aspect-Based Answer Relevance Evaluator**: Decomposes user questions into target sub-topics and verifies complete coverage without hallucination.
- **Grounded LLM Generation & Citation Verification**: Enforces inline citations `[1]`, `[2]`, validates citations against retrieved documents, and returns a structured insufficient-evidence fallback when evidence is missing.
- **Failure Classification & Case Inspection**: Classifies benchmark cases into failure categories (`Retrieval`, `Context`, `Generation`, `Citation`, `Evaluation`, `None`) with an interactive UI drawer.
- **Latency Monitoring**: Measures embedding, vector retrieval, MMR reranking, LLM generation, and total latency breakdown.
- **Reliability & Resilience**: Circuit breaking, exponential backoff retries for LLM API calls, rate limit handling, and health check endpoints (`/health`, `/health/services`).

---

## 💻 Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Vanilla CSS (Dark Space Aesthetic)
- **Backend**: Python 3.12, FastAPI, Pydantic, PyMuPDF, SQLite
- **Vector Database**: Qdrant Vector Search Engine
- **LLM & Embeddings**: Gemini Embedding (`gemini-embedding-001`), Gemini Flash (`gemini-2.5-flash`)
- **Testing & Quality Assurance**: Pytest (18 automated tests), GitHub Actions CI/CD, Docker Compose

---

## 🚀 Quick Start Guide

### Prerequisites
- Docker & Docker Compose **OR** Python 3.10+ & Node.js 20+

### Option 1: Docker Compose (Recommended)

1. Clone repository & prepare environment config:
   ```bash
   git clone https://github.com/your-username/KnowledgeOps.git
   cd KnowledgeOps
   cp .env.example .env
   ```

2. Start all services:
   ```bash
   docker compose up --build
   ```

3. Access platform endpoints:
   - **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
   - **FastAPI OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Qdrant Vector Dashboard**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

### Option 2: Local Development Setup

#### 1. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

---

## 🧪 Testing & Quality Engineering

### Run Pytest Test Suite
```bash
cd backend
python -m pytest tests -v
```
*Current test status: **18/18 passed** across chunking, reranking, vector search, answer relevance, citation verification, and answer quality scenarios.*

### Run Benchmark Suite (30 Cases)
```bash
cd backend
python run_benchmark.py
```

### Validate Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 📌 Known Limitations & Future Roadmap

1. **Synthetic Fallback Mode**: When `LLM_API_KEY` is not provided, the benchmark engine uses a deterministic fallback generator. For full generative reasoning, set a valid `LLM_API_KEY`.
2. **Dense Hybrid Search**: Hybrid search currently uses combined vector similarity + BM25 keyword matching. Future iterations will introduce native Sparse-Dense vector indexing.
3. **Multi-Modal PDF Extraction**: Current PDF parsing focuses on text content. Future roadmap includes OCR and table extraction via Unstructured/LayoutLM.

---

## 🛡️ License

MIT License — free for modification and enterprise reference architecture reuse.
