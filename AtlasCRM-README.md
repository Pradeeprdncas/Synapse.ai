# Atlas CRM — AI-Powered Project Management System

> An intelligent CRM that automates project tracking, task generation, and team communication — eliminating manual overhead for managers and HR through RAG-powered document intelligence.

---

## The Problem

Traditional CRMs require managers and HR to manually update project status, create tasks from PRDs, track progress, and communicate updates across teams. This takes hours every week and introduces human error.

**Atlas CRM removes that burden entirely.** Upload a PRD or project document. The system reads it, understands it, extracts tasks, assigns them, tracks progress, and keeps everyone updated — automatically.

---

## System Architecture Overview

```
Client (Web / Telegram Bot)
        │
        ▼
┌─────────────────────────┐
│   Backend API (Node.js) │  ← Authentication, Project Management, CRM Logic
│   Express + Prisma      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   RAG Microservice      │  ← Document Intelligence Engine
│   (Standalone Service)  │  ← Chunking, Embedding, Vector Search, Generation
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   LLM APIs              │  ← Mistral / OpenAI for generation
│   Vector Store          │  ← Embeddings and semantic search
│   Document Storage      │  ← PDF/DOCX processing pipeline
└─────────────────────────┘
```

---

## Version Roadmap

### ✅ V1 — Core MVP (Completed)
**Goal:** Build a working CRM with basic RAG integrated directly into the backend.

**What's built:**
- Full project management system — create projects, assign members, track tasks
- Document upload and processing pipeline
- Basic RAG implementation — PDF text extraction, keyword-based chunk retrieval
- AI-powered task generation from uploaded PRD documents
- Telegram bot integration (`@AtlasRAGbot`) for team notifications and queries
- JWT authentication with role-based access (Admin, Manager, Developer)
- Analytics dashboard, finance tracking, notification system

**Tech Stack:**
- Backend: Node.js, Express.js, Prisma ORM, MySQL
- Frontend: React, Vite
- RAG: PDF parsing, keyword-based chunking, Mistral AI for generation
- Bot: Telegram Bot API
- Auth: JWT, RBAC middleware

**Known Limitations (documented for V2):**
- RAG is tightly coupled to the main backend — slow document processing blocks API responses
- Keyword matching only — no semantic understanding, misses conceptually similar content
- No vector embeddings — retrieval quality degrades with complex queries
- Single bot integration only

**Baseline Performance (V1):**
| Operation | Time |
|-----------|------|
| Document upload + processing | ~8-12 seconds (synchronous) |
| Query retrieval (keyword) | ~200-400ms |
| Full query to answer | ~4-6 seconds |
| Max reliable document size | ~5MB |

---

### 🔄 V2 — RAG Microservice (In Progress)
**Goal:** Extract RAG into a standalone microservice with vector embeddings, semantic search, and multi-bot support.

**What's changing:**
- RAG becomes a **separate process** with its own API — decoupled from main backend
- Synchronous document processing replaced with **async job queue** (Bull + Redis)
- Keyword matching upgraded to **vector embeddings + semantic search**
- Chunk storage moved to **vector database** for similarity search
- Bot integrations expanded: Telegram (existing) + Discord + WhatsApp
- Each bot documents its own behavior, failure states, and response patterns

**Architecture change:**
```
V1: Frontend → Backend → [RAG inside backend] → LLM
V2: Frontend → Backend → Job Queue → RAG Microservice → Vector Store → LLM
                              ↑
                    Telegram / Discord / WhatsApp Bots
```

**Measurement targets for V2:**
- Document processing time (async, not blocking main API)
- Retrieval accuracy improvement over V1 keyword search
- Failure state reduction — target: zero unhandled failures
- Bot response time per platform

**V2 Telegram Bot:** [@AtlasRAGbot](https://web.telegram.org/k/#@AtlasRAGbot)

---

### 📋 V3 — RAG Research and Optimization (Planned)
**Goal:** Systematic improvement of every RAG component through measurement and experimentation. Target: process 100MB+ documents in under 15 seconds.

**Research areas:**

#### Chunking Experiments
| Method | Description | Measure |
|--------|-------------|---------|
| Fixed-size | Split every N characters | Speed vs accuracy |
| Sentence | Split at sentence boundaries | Context preservation |
| Paragraph | Split at paragraph breaks | Natural boundaries |
| Sliding window | Overlapping chunks | Boundary context |
| Semantic | Split at topic shifts | Best quality, highest cost |

**Target:** Find the optimal chunking method for legal/contract documents (railway tenders, PRDs).

#### Embedding Experiments
| Model | Dimensions | Speed | Quality |
|-------|-----------|-------|---------|
| all-MiniLM-L6-v2 | 384 | Fast | Good |
| all-mpnet-base-v2 | 768 | Medium | Better |
| text-embedding-3-small | 1536 | API cost | Best |

**Target:** Best accuracy-to-speed ratio for document types used in CRM.

#### Retrieval Experiments
| Method | Description |
|--------|-------------|
| Keyword (BM25) | Classic term matching |
| Semantic (cosine) | Vector similarity |
| Hybrid | Weighted combination |
| Reranking | Two-stage retrieval |
| MMR | Diversity-aware retrieval |

**Target:** Hybrid + reranking as final implementation.

#### Performance Targets
| Document Size | Target Processing Time |
|--------------|----------------------|
| 10MB | < 3 seconds |
| 50MB | < 8 seconds |
| 100MB | < 15 seconds |

**Scalability test:** Measure if processing time grows linearly or exponentially with document size. Fix exponential growth points.

**Bot integrations for V3:** Telegram + Discord + WhatsApp + Microsoft Teams + Slack

---

### 🎨 V4 — Frontend and Backend Overhaul (Planned)
**Goal:** Production-grade UI and hardened backend.

- Complete frontend redesign — better project dashboards, real-time updates
- WebSocket integration for live project status updates
- Improved error handling across all services
- API rate limiting and security hardening
- Performance monitoring and alerting

---

### 🚀 V5 — Full System Merge and Production Release (Planned)
**Goal:** Merge all services into a production-deployable system with full documentation.

- Single deployment configuration for all services
- Complete API documentation
- End-to-end test suite
- Cost tracking dashboard (tokens used, API costs per project)
- Research paper documentation of V3 RAG experiments

---

## Experiment Log

> Every experiment in V3 is documented here. Format: what was tried, how it was measured, what improved.

### Experiment Template
```
Date: 
Experiment: 
Hypothesis: 
Method: 
Metric measured: 
Result: 
Conclusion: 
Next step: 
```

*Experiments will be added here as V3 progresses.*

---

## Running the Project

### V1 — Backend + Frontend
```bash
# Clone the repository
git clone https://github.com/Pradeeprdncas/[repo-name]

# Backend
cd backend
npm install
cp .env.example .env  # Add your API keys
npx prisma migrate dev
npm run dev

# Frontend
cd frontend
npm install
npm run dev
```

### V2 — With RAG Microservice
```bash
# Start main backend
cd backend && npm run dev

# Start RAG microservice (separate process)
cd rag-service && npm run dev

# Start Redis (required for job queue)
redis-server

# Start Telegram bot
cd bot && npm run dev
```

### Environment Variables Required
```
DATABASE_URL=
JWT_SECRET=
MISTRAL_API_KEY=
TELEGRAM_BOT_TOKEN=
REDIS_URL=
```

---

## Project Structure

```
atlas-crm/
├── backend/          # Main API server (Node.js + Express + Prisma)
├── frontend/         # React + Vite dashboard
├── rag-service/      # Standalone RAG microservice (V2+)
├── bots/
│   ├── telegram/     # @AtlasRAGbot
│   ├── discord/      # V3
│   └── whatsapp/     # V3
├── docs/
│   ├── V1_DOCUMENTATION.md
│   ├── V2_DOCUMENTATION.md
│   └── EXPERIMENT_LOG.md
└── README.md
```

---

## Why This Project Exists

Most CRMs are passive tools — they store information that humans enter. Atlas CRM is an **active system** — it reads documents, understands context, generates tasks, and keeps teams aligned without human intervention.

The goal is to answer the question: *what if your CRM could read your PRD and manage the project itself?*

---

## Current Status

| Version | Status | Branch |
|---------|--------|--------|
| V1 | ✅ Complete | `v1-stable` |
| V2 | 🔄 In Progress | `v2-dev` |
| V3 | 📋 Planned | - |
| V4 | 📋 Planned | - |
| V5 | 📋 Planned | - |

---

## Built by

**Pradeep Nagarajan** — AI Product Engineer and Technical Trainer  
[Portfolio](https://tanstack-start-app.pradeep-nagarajan.workers.dev) · [LinkedIn](https://linkedin.com/in/pradeep824567) · [GitHub](https://github.com/Pradeeprdncas)
