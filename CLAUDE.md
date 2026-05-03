# AI Student Assignment Feedback Generator

## Project Overview

An AI-powered system that accepts student essays (PDF, DOCX, TXT), extracts and preprocesses text, splits content into paragraphs, and returns **structured feedback**: paragraph-level commentary, rubric-based scores, overall summary, suggestions, and optional **heuristic plagiarism-pattern flags** (not internet Turnitin-style checks). Retrieval-Augmented Generation (RAG) pulls **rubrics** from the Django database and optionally uses **vector embeddings (FAISS)** for semantic chunk retrieval. A **single orchestration agent** coordinates the workflow (custom `FeedbackGenerationAgent` for the main pipeline; LangChain + LangGraph available for the `/api/feedback-agent/` path). The primary end-to-end API is **upload → extract → split → agent → JSON output**. A minimal **React + Tailwind** frontend targets the complete pipeline.

## Tech Stack

| Layer | Choice |
|--------|--------|
| **Backend** | Django 4.2, Django REST Framework |
| **Database** | SQLite (default); rubrics stored relationally (`Rubric`, categories, criteria, levels) |
| **LLM** | Groq API (`groq`, `langchain-groq`); default model `llama-3.3-70b-versatile` (configurable via `GROQ_MODEL`) |
| **RAG** | Simple: ORM retrieval + prompt injection; **optional** vector path: FAISS + `sentence-transformers` embeddings (`vector_index/`, `vector_cache/`) |
| **Agent** | Single agent: `feedback_system/feedback_agent.py`; alternate LangGraph flow in `langchain_integration.py` |
| **Frontend** | Create React App, TypeScript, Tailwind CSS (`feedback-frontend/`) |
| **CORS** | `django-cors-headers` (DEBUG allows all origins in settings for local/LAN dev) |

## Project Structure

```
AI_project/
├── manage.py
├── requirements.txt
├── .env                          # GROQ_API_KEY, etc. (never commit)
├── db.sqlite3                    # Rubrics + submissions data
├── assignment_feedback/          # Django project (settings, root urls)
├── feedback_system/              # Main application
│   ├── models.py                 # Rubric hierarchy, submissions
│   ├── urls.py                   # All /api/... routes under app
│   ├── pipeline_views.py         # CompletePipelineView (primary E2E API)
│   ├── views.py                  # Upload, extract, preprocess, legacy feedback
│   ├── text_extraction.py
│   ├── text_preprocessing.py
│   ├── llm_integration.py        # Groq client, paragraph prompts, low temperature
│   ├── rubric_rag.py             # RAG: retrieve rubric, inject into prompts; vector branch
│   ├── feedback_agent.py         # Single agent orchestration (main pipeline)
│   ├── langchain_integration.py  # LangChain/LangGraph path (feedback-agent API)
│   ├── langchain_config.py
│   ├── plagiarism_checker.py     # Heuristic pattern flags only
│   ├── json_validator.py         # Strict output shape checks
│   ├── vector_config.py          # FAISS paths, embedding model, top_k
│   ├── vector_store.py
│   ├── vector_retriever.py
│   ├── vector_indexer.py
│   ├── embedding_service.py
│   ├── chunking_strategy.py
│   ├── vector_views.py           # Build/rebuild index, debug retrieval
│   ├── agent_views.py
│   ├── rag_views.py
│   ├── rubric_views.py
│   ├── middleware.py             # Long-request handling for LLM routes
│   └── management/commands/      # vector index CLI
├── feedback-frontend/
│   ├── src/
│   │   ├── App.tsx               # Upload UI, calls complete-pipeline
│   │   ├── index.tsx
│   │   └── index.css             # Tailwind entry
│   └── package.json
├── docs/                         # Design, migration, and legacy documentation (*.md)
│   ├── feedback_system/          # e.g. VECTOR_RAG_*.md
│   └── feedback-frontend/        # FRONTEND_SETUP.md, README (CRA)
├── tests/                        # All automated + integration tests (see tests/README.md)
│   ├── integration/              # Pipeline / RAG / agent scripts
│   ├── feedback_system/          # Unit tests (vector RAG, LangChain, plagiarism)
│   └── fixtures/                 # Sample .txt files for manual testing
├── create_sample_rubrics.py      # Optional DB seed (not imported at runtime)
├── CLAUDE.md                     # This file
└── BUILD_LOG.md
```

**Knowledge base (RAG):** Rubric content lives in **`db.sqlite3`**. Vector artifacts default to **`vector_index/`** (`rubric_index.faiss`, `rubric_metadata.json`) and **`vector_cache/`** when embedding RAG is enabled.

## API Endpoints

Base URL prefix: **`/api/`** (see `assignment_feedback/urls.py` → `feedback_system.urls`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/complete-pipeline/` | **Primary E2E:** file upload + extract + preprocess + agent + structured JSON (scores, feedback, suggestions, `plagiarism_analysis` when present) |
| GET | `/api/pipeline-status/` | Pipeline capabilities / metadata |
| POST | `/api/extract-text/` | Extract plain text from uploaded file |
| POST | `/api/preprocess-text/` | Split/clean into paragraphs |
| POST | `/api/generate-feedback/` | Generate feedback (granular step) |
| POST | `/api/feedback-agent/` | LangChain/LangGraph agent path (same family of features, alternate internals) |
| GET | `/api/agent-architecture/` | Agent architecture info |
| GET | `/api/agent-workflow/` | Workflow description |
| POST | `/api/rubric-rag-feedback/` | RAG-focused feedback endpoint |
| GET | `/api/rag-explanation/` | How RAG is used (educational) |
| POST | `/api/rubric-retrieval/` | Retrieve rubric context |
| CRUD | `/api/rubrics/`, `/api/rubrics/<id>/`, nested categories/criteria/levels | Rubric management |
| GET | `/api/rubrics/search/`, `/api/rubrics/stats/` | Search and stats |
| CRUD | `/api/submissions/` | Assignment submissions |
| POST | `/api/vector/build-index/` | Build FAISS index from DB |
| POST | `/api/vector/rebuild-index/` | Full rebuild |
| GET | `/api/vector/status/` | Index status |
| POST | `/api/vector/test-search/` | Test semantic search |
| GET | `/api/vector/debug/` | Debug info |
| POST | `/api/vector/clear-cache/` | Clear embedding cache |

## Frontend

| Entry | Description |
|-------|-------------|
| `npm start` → `http://localhost:3000` | Single-page upload form; displays scores, paragraph feedback, suggestions, plagiarism panel |
| API target | Default `http://127.0.0.1:8000/api/complete-pipeline/` (ensure backend + CORS) |

**Note:** The SPA may use a smaller default Groq model in code for local rate limits; the backend default for `complete-pipeline` is **`llama-3.3-70b-versatile`** unless the request overrides `model`.

## Build Log (Prompt Sequence)

This section records how the system was specified and evolved, step by step (incremental build).

1. **Objective** — AI assignment feedback: PDF/DOCX/TXT → extract → paragraphs → rubric-aware feedback → simple RAG → single agent → structured JSON. Constraints: modular, no multi-agent product, Django backend, LLM for feedback, simple RAG.
2. **Django scaffold** — Project + `feedback_system` app, REST structure, file upload endpoint; no AI yet.
3. **Extraction** — PDF/DOCX/TXT extraction APIs with error handling, plain text output.
4. **Preprocessing** — Paragraph split + whitespace cleanup.
5. **LLM (Groq)** — Client wrapper, structured prompts, paragraph feedback, low temperature (~0.2); no RAG/agent yet.
6. **Rubric system** — Structured rubrics (argument, evidence, grammar, etc.) in database/JSON, retrievable.
7. **Simple RAG** — Retrieve rubric from storage, inject into prompt, score against it (ORM-first; no mandatory vector DB).
8. **Single agent** — One orchestrator: paragraphs + RAG + LLM + combined final output (no multi-agent swarm).
9. **Strict JSON** — Enforced shape: paragraph feedback, rubric scores, overall feedback, suggestions; validation layer.
10. **Full pipeline** — Upload → extract → split → agent → single API; integration tests.
11. **React frontend** — Minimal Tailwind UI: upload, scores, feedback display.
12. **Quality pass** — Errors, prompts, edge cases; avoid unnecessary complexity.
13. **Vector RAG upgrade** — FAISS + embeddings, chunking, indexing service, retrieval with fallback to non-vector mode, admin-style reindex endpoints, tests for index/retrieval/fallback.
14. **Groq model migration** — Standardize on `llama-3.3-70b-versatile` in backend defaults/docs where applicable.
15. **LangChain + LangGraph** — Optional parallel path for agent internals; preserve API contracts where possible; `feedback_agent` remains central to `complete-pipeline`.
16. **Plagiarism heuristics** — `plagiarism_checker.py`: local patterns only (repetition, citation shifts, style jumps, patchwork, optional corpus overlap); `plagiarism_analysis` / risk level in JSON; `ENABLE_PLAGIARISM_CHECK` env toggle.

## Coding Standards

### General

- Never commit secrets; use **environment variables** (`.env` loaded manually or exported before `runserver` — Django does not auto-load `.env` unless you add that).
- Prefer **small, focused functions** and clear names.
- **Handle errors explicitly** in views and LLM calls; return structured JSON errors for API failures.
- Avoid drive-by refactors unrelated to the task at hand.

### Backend (Django)

- Follow **PEP 8**; keep views thin where possible — heavy logic in services/modules (`rubric_rag.py`, `feedback_agent.py`, `llm_integration.py`).
- Use **Django ORM** for rubrics and submissions.
- **Groq** calls should go through **`llm_integration.GroqLLMClient`** (and LangChain wrappers where that path is used).
- **Prompts** live in **`llm_integration.py`** (and LangChain message builders in `langchain_integration.py`) — avoid scattering duplicate prompt strings.
- Validate and sanitize uploads (size, type) in pipeline/views.
- Prefer **structured JSON responses** for APIs; use **`json_validator.py`** for pipeline output shape.
- **Single agent** for main product story: `FeedbackGenerationAgent` — do not introduce multi-agent orchestration for the same user journey without an explicit product decision.

### Frontend (React)

- **Functional components + hooks** only.
- Tailwind for layout/styling; **`App.tsx`** currently holds main UI (split into components only when it helps clarity).
- Always show **loading** and **error** states for uploads and API failures.

### AI / RAG

- **Temperature** stays low for consistent grading (see `llm_integration` / `LangChainConfig`).
- **RAG**: rubric text must be grounded in retrieved DB (and vector chunks when enabled).
- **Plagiarism**: communicate clearly as **heuristic / not proof** in UI and API notes.

### Git

- Do not commit `.env` or API keys.
- Use conventional prefixes where helpful: `feat:`, `fix:`, `test:`.

### Agents folder note

This repo keeps orchestration in **`feedback_system/feedback_agent.py`** (and **`langchain_integration.py`** for the alternate API). If you standardize on a physical `/agents` package later, migrate imports carefully and update this document.

## Environment Variables

```env
# Required for LLM
GROQ_API_KEY=

# Optional overrides
GROQ_MODEL=llama-3.3-70b-versatile
ENABLE_PLAGIARISM_CHECK=true
USE_VECTOR_RAG=true
SIMILARITY_THRESHOLD=0.7
TOP_K=5
ENABLE_LANGCHAIN=true
ENABLE_LANGGRAPH=true
LANGCHAIN_TEMPERATURE=0.2

# Django
DJANGO_SECRET_KEY=  # use SECRET_KEY in production via settings
DEBUG=True
```

Vector paths and embedding model defaults are in **`feedback_system/vector_config.py`** (e.g. `vector_index/`, `sentence-transformers/all-MiniLM-L6-v2`).

## Running the Project

### Backend

```bash
cd /path/to/AI_project
source venv/bin/activate
pip install -r requirements.txt
export GROQ_API_KEY="your-key"   # or: set -a && source .env && set +a
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Optional: seed rubrics — `python create_sample_rubrics.py` (if your workflow uses it).

### Frontend

```bash
cd /path/to/AI_project/feedback-frontend
npm install
npm start
```

Open **`http://localhost:3000`** (or use LAN URL only if CORS/DEBUG settings allow).

### Vector index (optional)

After rubrics exist in DB, call **`POST /api/vector/build-index/`** or use management commands under `feedback_system/management/commands/`.

### Tests

```bash
cd /path/to/AI_project
source venv/bin/activate
python manage.py test tests
# python tests/integration/test_rag_system.py
```

## Validation Checklist (Quick)

- [ ] `GROQ_API_KEY` set; pipeline returns `success: true` for a small `.txt` essay.
- [ ] Rubrics present in DB for the chosen `assignment_type`.
- [ ] Frontend shows scores, paragraph feedback, and plagiarism section when API includes `plagiarism_analysis`.
- [ ] With vector RAG off or index missing, system falls back without crashing (check logs).
- [ ] No secrets in git; `.env` local only.

---

*This file is tailored to the repository layout and behavior as of the last update. If you rename models, default models, or split the frontend, update **Project Structure**, **API Endpoints**, and **Environment Variables** to match.*
