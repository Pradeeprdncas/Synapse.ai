# V1 Documentation — Atlas CRM MVP

> Status: ✅ Complete and Stable  
> Tagged: v1.0  
> Date completed: May 2026

---

## What V1 Does

Atlas CRM V1 is a functional project management system where:

1. Admin creates a project and uploads a PRD document
2. System extracts text from the document using PDF parser
3. RAG pipeline chunks the text and stores it locally
4. AI reads the chunks and generates a structured task list
5. Tasks are assigned to developers automatically
6. Team receives notifications via Telegram bot
7. Managers can query the bot to get project status updates
8. Dashboard shows project progress, tasks, timelines, and finance tracking

---

## Architecture

```
User uploads PRD
      │
      ▼
Backend API (Node.js + Express)
      │
      ├── Prisma ORM → MySQL Database
      │     (projects, tasks, users, documents)
      │
      └── RAG Module (embedded in backend)
            │
            ├── PDF text extraction (pdf-parse)
            ├── Text chunking (fixed-size, keyword-based)
            ├── Chunk storage (JSON files / database)
            ├── Query → keyword match → top 5 chunks
            └── Mistral AI → generate answer
                        │
                        ▼
              Telegram Bot (@AtlasRAGbot)
              sends response to user
```

---

## Tech Stack

| Layer | Technology | Why chosen |
|-------|-----------|------------|
| Backend | Node.js + Express | Fast to build, familiar ecosystem |
| ORM | Prisma | Clean schema management, type safety |
| Database | MySQL | Relational structure fits project/task model |
| Frontend | React + Vite | Fast development, component-based |
| PDF Processing | pdf-parse | Simple text extraction from PDFs |
| AI Generation | Mistral AI | Cost-effective, good quality responses |
| Bot | Telegram Bot API | Easy integration, widely used |
| Auth | JWT + RBAC | Secure, stateless authentication |

---

## What Works in V1

- User registration and login with JWT
- Role-based access — Admin, Manager, Developer see different views
- Create and manage projects with team assignment
- Upload PRD documents (PDF/DOCX)
- AI-generated task list from uploaded documents
- Task tracking with status updates
- Telegram bot for querying project status
- Basic analytics dashboard
- Finance tracking per project
- Notification system for task updates

---

## Known Limitations (Fixed in V2)

**Performance:**
- Document processing is synchronous — blocks the API for 8-12 seconds during upload
- Large documents (5MB+) cause timeout errors
- No job queue — concurrent uploads cause server strain

**RAG Quality:**
- Keyword matching only — misses conceptually related content
- No vector embeddings — "contract expiry" won't match "when does the agreement end"
- Fixed-size chunking breaks sentences at arbitrary points losing context
- No reranking — top 5 chunks may not be the most relevant 5

**Architecture:**
- RAG is tightly coupled to backend — cannot scale independently
- Single bot integration only (Telegram)
- No retry logic if AI API call fails

---

## Baseline Performance Numbers

These numbers are measured on V1 and used as comparison baseline for V2 and V3 improvements.

| Operation | Time | Notes |
|-----------|------|-------|
| PDF text extraction | ~1-2 seconds | Depends on file size |
| Text chunking | ~0.1-0.3 seconds | Fixed-size, simple |
| Query keyword retrieval | ~200-400ms | Searches stored chunks |
| Mistral AI generation | ~2-4 seconds | API latency |
| Full query to answer | ~4-6 seconds | End to end |
| Document upload blocking time | ~8-12 seconds | Blocks main API |
| Max reliable document size | ~5MB | Larger causes timeouts |

---

## How to Run V1

```bash
git clone https://github.com/Pradeeprdncas/[repo-name]
cd v1

# Install dependencies
npm install

# Set up environment
cp .env.example .env
# Add: DATABASE_URL, JWT_SECRET, MISTRAL_API_KEY, TELEGRAM_BOT_TOKEN

# Set up database
npx prisma migrate dev

# Start server
npm run dev

# Start Telegram bot (separate terminal)
cd bot
npm run dev
```

---

## V1 Telegram Bot

**Bot:** [@AtlasRAGbot](https://web.telegram.org/k/#@AtlasRAGbot)

**What it does in V1:**
- Receive project status queries
- Query the RAG system and return AI-generated answers
- Send task assignment notifications to developers
- Alert managers when tasks are updated

**Commands:**
```
/start — Initialize bot and link to project
/status [project-name] — Get current project status
/tasks — List pending tasks
/query [question] — Ask anything about the project documents
```

---

## What V2 Fixes

| V1 Problem | V2 Solution |
|-----------|------------|
| Synchronous document processing | Async job queue with Bull + Redis |
| Keyword matching only | Vector embeddings + semantic search |
| RAG coupled to backend | Standalone RAG microservice |
| Single bot | Telegram + Discord + WhatsApp |
| No retry logic | Full error handling and retry |
| Timeouts on large files | Streaming processing, no size limit |

---

## Files in V1

```
v1/
├── backend/
│   ├── src/
│   │   ├── controllers/     # Project, Task, User, Document controllers
│   │   ├── middleware/       # JWT auth, RBAC
│   │   ├── routes/           # API route definitions
│   │   ├── services/
│   │   │   └── rag/          # PDF parsing, chunking, retrieval
│   │   └── utils/
│   ├── prisma/
│   │   └── schema.prisma     # Database schema
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/            # Dashboard, Projects, Tasks
│   │   └── components/
│   └── vite.config.js
└── bot/
    └── telegram/             # @AtlasRAGbot implementation
```

---

## Decision Log

**Why Mistral over OpenAI for V1?**
Cost. Mistral is approximately 10x cheaper than GPT-4 for similar quality on structured document tasks. At MVP stage with unknown query volume, cost predictability matters.

**Why keyword search over vectors for V1?**
Speed of implementation. Vector embeddings require choosing an embedding model, setting up a vector store, and managing dimensions. Keyword search works immediately. V2 upgrades this with full measurement of the quality difference.

**Why Telegram first?**
Lowest implementation friction. Telegram Bot API is free, well-documented, and requires no business verification. WhatsApp requires Meta Business API approval. Telegram validates the bot concept before investing in more complex integrations.

---

*V1 is locked. No further changes. All improvements go into V2.*
