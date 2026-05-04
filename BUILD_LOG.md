# AI Student Assignment Feedback Generator

**Build log & project handbook** (companion to `CLAUDE.md`).

---

## Project Overview

An AI-powered **student assignment feedback** system where educators or students upload an essay and receive a structured evaluation:

- **Multi-format upload:** PDF, DOCX, or plain text
- **Text extraction and cleaning** with clear error handling
- **Paragraph-level segmentation** for localized feedback
- **Rubric-aligned scoring** (argument, evidence, grammar-style criteria stored in the database)
- **Simple RAG:** retrieve rubric from storage, inject into LLM prompts; optional **vector embeddings (FAISS)** for semantic chunk retrieval
- **Single orchestration agent** (`FeedbackGenerationAgent`) for the main pipeline — no multi-agent product design
- **Structured JSON output:** paragraph feedback, rubric scores, overall summary, suggestions
- **Heuristic plagiarism-pattern analysis** (local flags only — not web-wide plagiarism verification)
- **Minimal React + Tailwind** UI for upload and results (scores, feedback, integrity panel)

---

## Tech Stack

- **Backend:** Django 4.2, Django REST Framework
- **Database:** SQLite (default); relational rubric models (`Rubric`, categories, criteria, levels)
- **Frontend:** React (Create React App), TypeScript, Tailwind CSS
- **AI:** Groq API (`llama-3.3-70b-versatile` default on backend; frontend may use a smaller model for local testing)
- **RAG extras:** FAISS + sentence-transformers (optional); ORM fallback always available
- **Agent (alternate path):** LangChain + LangGraph for `/api/feedback-agent/` — main E2E flow uses custom agent in `feedback_agent.py`
- **Auth:** Not required for the default demo pipeline (no DRF token gate on `complete-pipeline`); add if you harden for production

---

## Project Structure

```
AI_project/
├── manage.py
├── requirements.txt
├── .env
├── db.sqlite3
├── docs/                         # All project markdown except CLAUDE.md & BUILD_LOG.md
│   ├── …                        # Root-level notes (RAG, pipeline, migrations, etc.)
│   ├── feedback_system/
│   └── feedback-frontend/
├── BUILD_LOG.md
├── CLAUDE.md
├── assignment_feedback/          # Django project (settings, root urls)
│   ├── settings.py
│   └── urls.py
├── feedback_system/              # Main app
│   ├── models.py
│   ├── urls.py
│   ├── admin.py
│   ├── serializers.py
│   ├── views.py                  # Extract, preprocess, generate-feedback, submissions
│   ├── pipeline_views.py         # complete-pipeline (E2E)
│   ├── rubric_views.py
│   ├── rag_views.py
│   ├── agent_views.py
│   ├── vector_views.py
│   ├── text_extraction.py
│   ├── text_preprocessing.py
│   ├── llm_integration.py        # Groq client; prompts / generation
│   ├── rubric_rag.py             # RAG retrieval + prompt augmentation
│   ├── feedback_agent.py         # Single agent orchestration (primary)
│   ├── langchain_integration.py  # LangGraph path
│   ├── langchain_config.py
│   ├── plagiarism_checker.py
│   ├── json_validator.py
│   ├── middleware.py
│   ├── vector_config.py
│   ├── vector_store.py
│   ├── vector_retriever.py
│   ├── vector_indexer.py
│   ├── embedding_service.py
│   ├── chunking_strategy.py
│   └── management/commands/
├── feedback-frontend/
│   ├── src/
│   │   ├── App.tsx               # Main UI + fetch to complete-pipeline
│   │   ├── index.tsx
│   │   ├── index.css
│   │   ├── App.css
│   │   └── __tests__/App.test.tsx
│   └── package.json              # CRA README: docs/feedback-frontend/README.md
├── vector_index/                 # Created when vector index is built (gitignore if sensitive/large)
├── vector_cache/
├── tests/
│   ├── integration/
│   ├── feedback_system/
│   └── fixtures/
└── create_sample_rubrics.py
```

**Where “knowledge” lives:** rubric rows in **`db.sqlite3`**; vector sidecar files under **`vector_index/`** and **`vector_cache/`** when embedding RAG is enabled.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/complete-pipeline/` | End-to-end: upload → extract → preprocess → agent → JSON (scores, feedback, suggestions, `plagiarism_analysis` when enabled) |
| GET | `/api/pipeline-status/` | Pipeline info and capabilities |
| POST | `/api/extract-text/` | Extract plain text from file |
| POST | `/api/preprocess-text/` | Paragraph list + cleanup |
| POST | `/api/generate-feedback/` | Feedback generation step |
| POST | `/api/feedback-agent/` | LangChain/LangGraph agent endpoint |
| GET | `/api/agent-architecture/` | Agent architecture metadata |
| GET | `/api/agent-workflow/` | Workflow metadata |
| POST | `/api/rubric-rag-feedback/` | RAG-centric feedback |
| GET | `/api/rag-explanation/` | RAG explanation (docs/education) |
| POST | `/api/rubric-retrieval/` | Retrieve rubric context |
| * | `/api/rubrics/`, nested `/categories/`, `/criteria/`, `/levels/` | Rubric CRUD |
| GET | `/api/rubrics/search/` | Search rubrics |
| GET | `/api/rubrics/stats/` | Rubric stats |
| * | `/api/submissions/` | Submission list/detail |
| POST | `/api/vector/build-index/` | Build FAISS index from DB |
| POST | `/api/vector/rebuild-index/` | Rebuild index |
| GET | `/api/vector/status/` | Index status |
| POST | `/api/vector/test-search/` | Test semantic search |
| GET | `/api/vector/debug/` | Debug retrieval |
| POST | `/api/vector/clear-cache/` | Clear embedding cache |

All app routes are mounted under **`/api/`** (see `assignment_feedback/urls.py`).

---

## Frontend Pages

| Route | Page | Access |
|-------|------|--------|
| `/` (CRA dev server) | Upload essay, assignment type, optional context; displays scores, paragraph feedback, suggestions, plagiarism panel | Public (local demo) |

There is no multi-route SPA router in the default template — everything is in **`App.tsx`**. Add React Router only if you split pages later.

---

## Coding Standards

### General

- Never hardcode secrets or API keys — use environment variables (and never commit `.env`).
- Prefer single-responsibility functions and descriptive names.
- Handle errors explicitly; return structured JSON errors from APIs where possible.
- Keep changes scoped: do not refactor unrelated modules when fixing one feature.

### Backend (Django)

- Follow **PEP 8**.
- Use **Django ORM** for rubrics and submissions.
- Centralize **Groq** usage in **`feedback_system/llm_integration.py`** (and LangChain wrappers in **`langchain_integration.py`** for that code path).
- Keep **views thin**; orchestration belongs in **`feedback_agent.py`** and RAG logic in **`rubric_rag.py`**.
- Return **structured JSON** from REST views; pipeline output is validated with **`json_validator.py`**.
- Maintain **one primary agent** for the product story; avoid multi-agent complexity unless explicitly required.

### Frontend (React)

- Use **functional components and hooks** only.
- Use **Tailwind** utilities; `App.css` is legacy CRA — prefer Tailwind for new UI.
- Always surface **loading** and **error** states for the upload / API call.
- *Ideal:* move `fetch` into a small `src/api/` module; current code calls `fetch` inside `App.tsx` (acceptable for a minimal demo).

### AI / Prompts

- Keep **temperature low** (~0.2) for consistent grading.
- Prompts should ask for **structured** model output; validate before treating as final.
- **Plagiarism copy** must stay non-accusatory; flags are **heuristic**, not proof.

### Agents

- Primary orchestration: **`feedback_system/feedback_agent.py`**.
- Alternate: **`langchain_integration.py`**. If you later introduce a top-level **`/agents`** package, migrate imports deliberately and update this doc.

### Git

- Use clear messages: `feat:`, `fix:`, `test:`, `refactor:`.
- Never commit `.env` or keys.

---

## Environment Variables

```env
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
ENABLE_PLAGIARISM_CHECK=true
USE_VECTOR_RAG=true
SIMILARITY_THRESHOLD=0.7
TOP_K=5
ENABLE_LANGCHAIN=true
ENABLE_LANGGRAPH=true
LANGCHAIN_TEMPERATURE=0.2
DEBUG=True
```

Load into the shell before `runserver` if you rely on `.env` (Django does not load `.env` automatically unless you add `python-dotenv` / manual `source`).

---

## Running the Project

### Backend

```bash
cd AI_project
source venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a   # or: export GROQ_API_KEY=...
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Frontend

```bash
cd AI_project/feedback-frontend
npm install
npm start
```

### Tests

```bash
cd AI_project
source venv/bin/activate
python manage.py test tests
```

See `tests/README.md` for integration scripts (`tests/integration/…`).

### Vector index (optional)

After rubrics exist: `POST /api/vector/build-index/` or Django management commands under `feedback_system/management/commands/`.

---

## Chronological Build Log

How this codebase was specified and grown (aligned with the prompts you used step by step).

| Step | Milestone | What shipped (conceptually) |
|------|-----------|-----------------------------|
| 1 | Objective | Single-agent, Django, simple RAG, structured JSON, no multi-agent swarm |
| 2 | Django scaffold | `assignment_feedback` + `feedback_system`, DRF, upload endpoint skeleton |
| 3 | Extraction | PDF/DOCX/TXT → plain text API, errors as JSON |
| 4 | Preprocessing | Paragraph split + whitespace cleanup |
| 5 | LLM (Groq) | Client wrapper, paragraph feedback, low temperature |
| 6 | Rubric system | DB (and/or structured) rubrics, CRUD APIs |
| 7 | Simple RAG | ORM retrieve rubric → inject into prompt → score |
| 8 | Single agent | `FeedbackGenerationAgent`: preprocess → RAG → LLM → aggregate |
| 9 | Strict JSON | Schema validation; paragraph + rubric + overall + suggestions |
| 10 | Full pipeline | `CompletePipelineView`: upload → extract → split → agent → response |
| 11 | React UI | CRA + Tailwind; upload + results |
| 12 | Quality | Errors, prompts, edge cases |
| 13 | Vector RAG | FAISS, embeddings, chunking, index build/rebuild, retrieval + **fallback** |
| 14 | Model migration | Groq default `llama-3.3-70b-versatile` across backend/config/docs |
| 15 | LangChain/LangGraph | Parallel internals for `feedback-agent` API; preserve contracts |
| 16 | Plagiarism heuristics | `plagiarism_checker.py`, `plagiarism_analysis` in JSON, `ENABLE_PLAGIARISM_CHECK` |
| 17 | Hardening / UX | CORS for CRA/LAN, optional `plagiarism_analysis` in API + frontend display |

*Dates are intentionally omitted — update this table when you tag releases.*

---

## Validation Checklist

- [ ] Backend starts; `GET /api/pipeline-status/` or health via Django.
- [ ] `POST /api/complete-pipeline/` succeeds with a small `.txt` and `GROQ_API_KEY` set.
- [ ] Rubric exists in DB for the `assignment_type` you send.
- [ ] Frontend shows scores and paragraph feedback without console CORS errors.
- [ ] Vector path: index builds OR system falls back to ORM RAG without crashing.
- [ ] No secrets in git.

---


