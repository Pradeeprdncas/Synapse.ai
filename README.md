# Atlas Agent

Atlas turns project requirements into traceable, human-approved execution.

Teams lose time translating PRDs into tasks, assigning work, preserving requirement traceability, and keeping developers informed. Atlas reads a PRD, extracts explicit requirements, proposes implementation work, evaluates team skills and workload, recommends an assignee, waits for human approval, and sends the selected developer the relevant context.

## User and team administration

Atlas separates the application-level `ADMIN` role from project membership roles. Admins can create and edit users (including other admins), create a project for a selected manager, and administer every project. Managers can add existing users to their projects as `MANAGER`, `TEAM_LEAD`, `SENIOR_DEVELOPER`, `JUNIOR_DEVELOPER`, or `INTERN`, with explicit skills and capacity.

When the creating admin has connected Gmail, account creation can email the user's initial credentials. Passwords are always hashed in the database. The top-right profile control opens Settings, where users can change their name, email, and password; password changes require the current password.

Create or promote a local administrator without putting a password in source code:

```bash
cd backend
python -m scripts.create_admin --name "Local Admin" --email "admin@example.test" --password "choose-a-temporary-password"
```

After signing in, use **Team → Create user**, then select a project and add the user with a project role. Admins select the initial manager in the new-project form.

## Lamatic AgentKit Challenge

### Problem

Project-management tools store work after people have already interpreted the specification. The difficult part—understanding the PRD, deciding what must be built, assigning it responsibly, and proving why the task exists—remains manual.

### Solution

Atlas is an AI-assisted project execution loop with deterministic safety boundaries:

```text
PRD / Google Doc
        ↓
Structure-Aware Chunking
        ↓
Project-Scoped Qdrant Retrieval
        ↓
Requirements + Provenance
        ↓
Task Proposals
        ↓
Human Approval
        ↓
Complexity + Assignment Engine
        ↓
Human Approval
        ↓
Assignment
        ↓
Gmail + Relevant Context
        ↓
Execution
        ↓
Coverage / Health / Workload / Activity
```

The challenge flow demonstrates requirement interpretation, non-binding task proposals, approval-gated mutations, explainable assignment, requirement-to-task traceability, focused context delivery, and project-state measurement.

### AI and deterministic responsibilities

AI-shaped responsibilities:

- Requirement interpretation
- Task-proposal generation
- Optional complexity assistance
- Assignment explanations and summaries

Deterministic application responsibilities:

- Authentication and backend RBAC
- Project and vector isolation
- Schema/confidence validation
- Approval-state transitions
- Task and assignment mutation
- Assignment scoring and workload
- Coverage and project-health calculations
- Notification execution and idempotency

Document text is untrusted input. It is data for extraction and retrieval; it cannot grant permissions, change system policy, approve work, assign users, or send email.

## Architecture

- FastAPI and strict Pydantic request/output models
- SQLAlchemy with ordered Alembic migrations
- React/TanStack Start frontend
- Local Qdrant collection with deterministic 256-dimensional hashed embeddings
- Gmail API and Google Docs API via authorization-code OAuth
- Fernet-encrypted Google access and refresh tokens

The lightweight local Qdrant adapter requires no paid vector service or model download. Its embedding adapter is replaceable; the project-isolation contract and payload metadata remain stable.

## RAG and structure-aware chunking

Markdown headings are maintained as a hierarchy such as `Authentication > Session Management`. Paragraphs and intact lists remain grouped under their heading. Long prose is split at sentence boundaries with an approximately 3,600-character target and 12% overlap.

Every vector payload contains:

- `project_id`, `document_id`, and optional `requirement_id`
- deterministic `chunk_id`
- heading/section and source filename
- chunk index and chunking method
- creation timestamp and chunk text

Qdrant retrieval applies `project_id` as a mandatory query-level filter. Results are not merely filtered after retrieval. Deleting a document also deletes its project-and-document-scoped vectors.

Run the bundled evaluation:

```bash
cd backend
PYTHONPATH=. python3 scripts/evaluate_chunking.py
```

Current four-query demo result:

| Strategy | Chunks | Top-k hits | Hit rate | Irrelevant results |
|---|---:|---:|---:|---:|
| Basic fixed-word | 2 | 4/4 | 100% | 0 |
| Structure-aware | 4 | 4/4 | 100% | 0 |

The small fixture shows equal retrieval accuracy, so no accuracy improvement is claimed. The measured benefit is finer source provenance and retained heading context.

## Human approval and traceability

Generated proposals are persisted separately from tasks. A Manager must approve or reject proposals. Approval creates one task and copies requirement links into `task_requirements`; repeated approval returns a conflict and cannot create a duplicate task.

Coverage is computed from persisted links:

- Covered: a task link exists.
- Partially covered: a pending proposal link exists, but no task link exists.
- Uncovered: neither exists.
- Percentage: `covered / total * 100`.

The task traceability and assignment-context APIs answer “Why does this task exist?” using stored requirement IDs, source sections, source text, and documents.

## Project RBAC

Project roles are separate from the application-level `User.role`.

| Role | Project capabilities |
|---|---|
| `MANAGER` | Documents, analysis, proposal review, tasks, assignments, members, analytics, settings/activity |
| `TEAM_LEAD` | Review generated work, create/update tasks, recommend/approve assignments, workload/health/activity |
| `SENIOR_DEVELOPER` | Project requirements and related work; update own assigned task status/checklist |
| `JUNIOR_DEVELOPER` | Assigned tasks and linked requirement context; update own status/checklist |
| `INTERN` | Assigned tasks and linked requirement context; limited status transitions |

Permissions are enforced in FastAPI routes. Hidden frontend actions are not treated as authorization.

## Explainable assignment

Recommendations are deterministic and total at most 100 points:

| Component | Range |
|---|---:|
| Required skill match | 0–40 |
| Role fit for complexity | 0–25 |
| Current capacity | 0–20 |
| Dependency/context fit | 0–10 |
| Priority fit | 0–5 |

Complex work favors Team Leads and Senior Developers. Simple work can favor Junior Developers or Interns. Active and high-priority tasks reduce capacity points. Interns are disqualified from security, authentication, authorization, payment, permissions, and architecture work. Atlas stores the score, component breakdown, reasons, and alternatives, but cannot assign the task until an authorized Manager or Team Lead approves it.

## Gmail context delivery

Assignment approval commits task ownership before attempting Gmail. A Gmail failure never rolls back the assignment.

The context resolver follows only:

```text
Assigned task → linked requirements → requirement source documents
```

It deduplicates source documents and excludes unrelated project files. The email includes project/task details, priority, complexity, requirement IDs/descriptions, acceptance criteria, source sections, assignment reasons, relevant document links or attachments, and an Atlas task link.

Small local files may be attached. Oversized files use a time-limited signed URL whose recipient must still have active project access. Google Docs use their provider URL. Internal filesystem paths and provider tokens are never returned.

Delivery states are `SENT`, `FAILED`, or skipped/disabled. The unique key `assignment:{task_id}:{assignee_id}:initial` prevents duplicate email; a failed delivery may be retried by an authorized approver.

## Google integration

Atlas uses authorization-code OAuth with a random state stored only as a SHA-256 hash, a ten-minute expiry, and one-time consumption. Access and refresh tokens are encrypted at rest and never sent to the frontend. Scopes are limited to identity/email, Gmail send, and Google Docs read-only.

Google Doc import uses the same structure-aware chunk/database/Qdrant ingestion path as uploaded files.

### Live Google verification

On 15 August 2026, the project owner manually verified the configured local integration end to end:

- Google OAuth consent and callback completed, and the connection persisted.
- A real Google Doc imported through the normal Atlas ingestion pipeline and produced requirements.
- An assignment recommendation was generated and approved by a human.
- Gmail delivered the assignment with the correct task and relevant requirement/document context.
- Duplicate assignment/notification behavior was checked.

These are owner-supplied manual verification results. They are separate from the automated OAuth-state, context-selection, Gmail MIME, failure, retry, and idempotency tests.

For local development, configure:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback
GOOGLE_FRONTEND_SUCCESS_URL=http://localhost:8080/settings?google=connected
GOOGLE_TOKEN_ENCRYPTION_KEY=
ATLAS_API_PUBLIC_URL=http://127.0.0.1:8000
ATLAS_FRONTEND_URL=http://localhost:8080
ATLAS_EMAIL_ATTACHMENT_MAX_MB=10
```

Register this exact local redirect URI in Google Cloud:

```text
http://127.0.0.1:8000/google/oauth/callback
```

Register both local JavaScript origins:

```text
http://localhost:8080
http://127.0.0.1:8080
```

Deployment URLs are intentionally not guessed. Replace the environment values with the deployed HTTPS backend callback and frontend settings URL, then register those exact values in Google Cloud.

## Run locally

Requirements: Python 3.11+, Node.js, and npm.

```bash
cp .env.example .env

cd backend
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd rag-frontend
npm install
npm run dev -- --host 127.0.0.1 --port 8080
```

Open `http://127.0.0.1:8080/login`.

## Demo team

Choose a temporary non-production password at runtime and seed an existing project:

```bash
cd backend
ATLAS_DEMO_PASSWORD='choose-a-temporary-password' PYTHONPATH=. python3 scripts/seed_demo_team.py PROJECT_ID
```

This creates or updates fake `example.test` users for Maya (Manager), Arun (Team Lead), Priya (Senior Developer), Kumar (Junior Developer), and Nila (Intern). No demo password is stored in source.

## Test and verification

```bash
cd backend
python3 -m pytest -q
python3 -m compileall -q app scripts tests
python3 -m alembic upgrade head
PYTHONPATH=. python3 scripts/evaluate_chunking.py

cd ../rag-frontend
npm run build

cd ..
git diff --check
```

The isolated HTTP flow is available at `backend/scripts/verify_demo_flow.py`; run it with a temporary SQLite `DATABASE_URL` so it does not alter development data. Automated tests use mocked provider calls; the live Google verification above was performed manually by the project owner.

## 2–3 minute demo

1. **0:00–0:20 — Problem:** PRDs do not become accountable execution by themselves.
2. **0:20–0:35 — Architecture:** Show the approval-gated loop and deterministic safety boundary.
3. **0:35–1:00 — Requirements:** Upload `demo/atlas-agent-sample-prd.md`, analyze it, and show heading-aware provenance.
4. **1:00–1:20 — Tasks:** Open Proposed Tasks and approve one proposal; show the linked requirement and updated coverage.
5. **1:20–1:50 — Assignment:** Generate a recommendation and show skill, role, capacity, dependency, and priority points plus alternatives.
6. **1:50–2:10 — Approval:** Approve the recommendation; emphasize that Atlas could not mutate ownership before this action.
7. **2:10–2:30 — Context:** Show Gmail with the task, acceptance criteria, linked requirement, and only the relevant source document.
8. **2:30–2:50 — Execution:** Sign in as the assigned developer and update the task status.
9. **2:50–3:00 — Evidence:** Return to Overview/Activity and show workload, health, coverage, and the human/agent audit trail updating.

## Known limitations

- The deterministic hashed embedding is convenient and offline, but is not a production semantic embedding model.
- The conservative extractor recognizes explicit must/shall/should statements; a larger labelled evaluation set is needed for meaningful extraction recall.
- Gmail and Google Docs require valid credentials, consent, and network access in each environment; the configured local flow has been manually verified by the project owner.
- Tasks have no due date, so health returns `overdueTasks: null` and `overdueTrackingSupported: false`.
- Google People and Sheets are intentionally out of scope.
- Email delivery is synchronous after the assignment commit; production should move provider delivery to a durable worker/outbox.
