# Tests layout

| Location | Contents |
|----------|----------|
| **`tests/integration/`** | Scripts you can run with `python …` or include in `manage.py test`: pipeline, RAG demo, agent demo, plagiarism demo, broken-pipe HTTP check. |
| **`tests/feedback_system/`** | Django/pytest-friendly modules: LangChain, plagiarism checker, vector RAG. |
| **`tests/fixtures/`** | Sample files (`test_essay.txt`, `test_sample.txt`, etc.) for manual runs. |

**Django discovery:** The `tests` package is registered as app **`project_tests`** in `INSTALLED_APPS`. Run everything:

```bash
python manage.py test tests
```

Run one module:

```bash
python manage.py test tests.integration.test_complete_pipeline
python manage.py test tests.feedback_system.test_plagiarism_checker
```

**Run integration script directly:**

```bash
python tests/integration/test_rag_system.py
python tests/integration/test_agent_system.py
python tests/integration/test_plagiarism_detection.py
python tests/integration/test_complete_pipeline.py   # uses Django test runner via __main__
```

**Frontend (CRA):** `feedback-frontend/src/__tests__/App.test.tsx`
