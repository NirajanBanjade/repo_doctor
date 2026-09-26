# RepoDoc — Project-Wide Development Instructions

This file is the authoritative guide for all contributors and AI agents working on RepoDoc.
Read it before writing a single line of code. All architectural constraints in this file are binding.

---

## 1. Project Purpose

RepoDoc helps a new developer understand an unfamiliar codebase, verify the environment, assess the impact of a change, generate targeted regression tests, and prepare a pull request — all with evidence tied to concrete source references.

**Non-goal:** RepoDoc is not a code-generation product, a CI system, or an autonomous agent that merges or deploys code.

---

## 2. Canonical Product Name

The product is **RepoDoc**. Do not use "OnboardIQ" (an inconsistency in the original PRD).

---

## 3. Repository Layout

```
repodoc/
├── backend/          Python / FastAPI service
├── frontend/         React / TypeScript UI
├── sample_repo/      Seeded demo app (FastAPI + PostgreSQL + pytest)
├── docker/           Dockerfiles for backend and sandbox
├── docs/
│   ├── features/     One Markdown spec per major feature
│   └── api/          Shared API contracts and data schemas
├── ARCHITECTURE.md   System architecture (read before implementing)
└── AGENTS.md         This file
```

Never place application code in the root directory. Never put frontend code in `backend/` or vice versa.

---

## 4. Architectural Constraints (Non-Negotiable)

1. **Three-layer separation:** Frontend → Backend → Bob. The frontend never calls Bob directly. Bob never writes to the database directly.
2. **Backend owns state.** All session state, evidence, graph data, and test results live in SQLite under `backend/`. No state is stored in the frontend or in Bob.
3. **Bob outputs are validated before use.** Every response from a Bob agent is validated against its Pydantic schema in `app/bob/schemas/`. If validation fails, the raw output is stored in `bob_outputs.parsed_ok = false` and the operation is flagged — never silently accepted.
4. **The original repository clone is read-only.** All modifications (generated tests, fix patches) go into a `working_copy/` directory that is a separate copy. The sandbox mounts the working copy.
5. **No secrets in code, logs, or commits.** Environment variables only. The sandbox never exposes host environment variables.
6. **Developer approval is required** before: writing generated test files, applying fix patches, executing newly generated tests, or creating a PR summary. Approval must be recorded in `test_plans.status = 'approved'` before execution proceeds.
7. **Evidence labels are immutable downward.** An edge may only be promoted from `inferred` → `confirmed_static` → `observed_test`, never demoted. Promotion requires re-running the relevant adapter or obtaining a coverage trace result.
8. **Dynamic and unresolved calls are labeled `inferred` and displayed as such.** Never represent inferred edges as confirmed.
9. **Container isolation.** The sandbox Docker container must be disposable, resource-limited (CPU, memory, timeout), and network-isolated except for package mirrors. Never run unreviewed scripts on the host.
10. **No autonomous merging or deployment.** RepoDoc produces a PR summary and a patch; a human submits the PR.

---

## 5. Backend Coding Conventions (Python / FastAPI)

- **Python version:** 3.11+.
- **Formatter:** Black (line length 88). All code must pass `black --check` before commit.
- **Linter:** Ruff. Fix all errors; treat warnings as errors in CI.
- **Type hints:** Required on all function signatures. Use `from __future__ import annotations` at the top of every module.
- **Pydantic v2:** Use for all request/response models and Bob output schemas.
- **Async:** Use `async def` for all FastAPI route handlers and any I/O-bound service methods. Use `asyncio.to_thread` for blocking calls (subprocess, file I/O).
- **Imports:** Absolute imports only. No `from app import *`.
- **Error handling:**
  - Raise typed `HTTPException` with explicit status codes in route handlers.
  - Use a global exception handler for unexpected errors; log full tracebacks; return `500` with a generic message.
  - Never swallow exceptions silently.
- **Logging:** Use Python `logging` with structured JSON output (`python-json-logger`). Log every Bob agent invocation with `session_id`, `agent`, and `duration_ms`.
- **Database:** SQLAlchemy Core (not ORM) for SQLite. Migrations via Alembic. Never use raw string interpolation in SQL.
- **Tests:** pytest with `pytest-asyncio`. All backend modules must have a corresponding test file under `backend/tests/`. Minimum 80 % branch coverage for `analysis/` and `services/` modules.

---

## 6. Frontend Coding Conventions (React / TypeScript)

- **TypeScript strict mode** (`"strict": true` in tsconfig). No `any` without an explicit comment explaining why.
- **Formatter:** Prettier (default config). All code must pass `prettier --check` before commit.
- **Linter:** ESLint with `@typescript-eslint/recommended`. No lint errors in CI.
- **Component style:** Functional components with hooks only. No class components.
- **State management:** React Query for server state (API calls). React Context only for global UI state (e.g., current session ID). No Redux.
- **Graph rendering:** React Flow for architecture and impact graphs. Nodes and edges are typed using the interfaces in `frontend/src/types/`.
- **API client:** A single typed client in `frontend/src/api/client.ts` generated from (or matching) `docs/api/contracts.md`. No inline `fetch` calls in components.
- **Approval gates:** Any action that writes generated files or executes generated tests must pass through the `ApprovalModal` component with an explicit confirmation step. This is a UI safety constraint.
- **No sensitive data in the browser.** The frontend must not store repository credentials, environment secrets, or raw container logs beyond the current session's display buffer.
- **Tests:** Vitest + React Testing Library. Components under `TestPlanView` and `ApprovalModal` must have unit tests for the approval flow.

---

## 7. Language Adapter Conventions

- Every adapter must extend `AdapterBase` from `app/analysis/base_adapter.py`.
- `detect(repo_path)` must be fast (file-system check only, no parsing). It returns `True` if this adapter should process the repo.
- `extract_nodes` and `extract_edges` must be deterministic: same source tree → same output every run.
- Adapters must not make network calls, spawn Docker containers, or call Bob.
- All edges produced by adapters have `evidence_status = "confirmed_static"` by default.
- An adapter encountering a dynamic call (e.g., `getattr`, reflection, `eval`) must emit an edge with `evidence_status = "inferred"` and a `note` field describing the reason.
- The TypeScript adapter stub must return empty lists with a logged warning; it must never raise an exception.

---

## 8. IBM Bob Integration Rules

- Bob is invoked only from `app/bob/integration.py`. No other module may call Bob directly.
- Each agent invocation must be logged to `bob_outputs` table with raw response, `parsed_ok` flag, and timestamp.
- Pydantic schemas for Bob outputs live in `app/bob/schemas/`. Each schema has a `model_validate` method; validation failures raise `BobOutputValidationError`.
- When running parallel Bob agents (Architecture Agent + Documentation Agent; Impact Agent + Test Agent), the backend must launch them concurrently and await both before proceeding. Use `asyncio.gather`.
- Bob must not be given the ability to execute shell commands on the host. Only pass Bob the text content it needs (source snippets, README content, diff text, graph JSON).
- If the Bob invocation API is unavailable or returns an error, the backend degrades gracefully: the relevant feature displays a "Bob analysis unavailable" notice, but static analysis results are still shown.

---

## 9. Sandbox and Test Execution Rules

- The sandbox image is defined in `docker/Dockerfile.sandbox`. It is built once and reused per session.
- All test execution happens inside the sandbox via `app/sandbox/test_executor.py`. No pytest calls on the host.
- The sandbox container must have: CPU limit (1 core), memory limit (512 MB), execution timeout (120 s per run), no network access (or allow-listed package mirrors only).
- Generated test files are written to `working_copy/tests/generated/` before mounting into the sandbox.
- Sandbox stdout, stderr, exit code, and individual test results (parsed from pytest's JSON output `--json-report`) are persisted to `test_results`.
- A failed sandbox run (timeout, OOM, container exit > 0 for non-test reasons) must be reported as `infrastructure_error`, not as a test failure.

---

## 10. Evidence and Honesty Requirements

These rules directly implement the PRD's safety and reliability section (§8):

- **Never report a passing generated test as proof of safety.** The verification report must always list: skipped nodes, inferred edges, assertions that were not executed, and components with no applicable test.
- **Every confirmed edge must have** `file`, `line`, and `evidence_status = "confirmed_static"` or `"observed_test"` before it is displayed as confirmed.
- **Impact graph what-if risks** (behavior changes from a described intent) are labeled `hypothesis` and may only be promoted to `confirmed` if a test assertion validates them.
- **Setup instructions** are labeled `verified` only after a successful clean-container run, not after a human describes them as correct.

---

## 11. Feature Implementation Sequence

Features must be implemented in this order. Do not start a feature until its dependencies are complete and passing.

| Step | Feature | Depends on |
|---|---|---|
| 1 | Database schema and migrations | — |
| 2 | Session management API | Step 1 |
| 3 | Repo importer + Python adapter | Step 2 |
| 4 | Graph builder (NetworkX) | Step 3 |
| 5 | Repository X-Ray API + Architecture/Documentation Agents | Step 4 |
| 6 | Architecture map frontend | Step 5 |
| 7 | Docker sandbox runner | Step 2 |
| 8 | Environment Doctor | Steps 5, 7 |
| 9 | ImpactScope (BFS engine + Impact Agent) | Step 4 |
| 10 | Impact graph frontend | Step 9 |
| 11 | Test Mapper | Steps 9, 7 |
| 12 | Test Agent + Test Plan UI | Steps 11, 5 |
| 13 | Test Generator + Sandbox executor | Steps 12, 7 |
| 14 | Test Results frontend | Step 13 |
| 15 | Verification Agent + Report | Steps 13, 8 |
| 16 | FirstPR feature | Steps 6, 8 |
| 17 | Verification + PR Summary frontend | Step 15 |
| 18 | Sample repo seeded demo | All above |

---

## 12. Testing Requirements

- **Unit tests:** Required for every service module, adapter, and Bob schema validator.
- **Integration tests:** Required for every API route. Use `httpx.AsyncClient` with a test SQLite database.
- **Sandbox tests:** Test the sandbox runner with a known pytest fixture to confirm container lifecycle, timeout enforcement, and result parsing.
- **No tests are optional.** A PR that removes test coverage for a module without a documented reason will not be accepted.
- **Do not test Bob's internal behavior.** Mock `app/bob/integration.py` in all tests. Tests should verify that the backend correctly handles both valid Bob outputs and validation failures.

---

## 13. What to Do When the PRD Is Ambiguous

The PRD contains eight documented open questions (see `ARCHITECTURE.md §11`). When you encounter an ambiguity:

1. Check `ARCHITECTURE.md §11` first — it may already be listed.
2. If not listed, add it to `ARCHITECTURE.md §11` before proceeding.
3. Do not silently invent a requirement. Implement a stub that raises `NotImplementedError` with a description of the decision needed.
4. Open a discussion item rather than guessing at integration behavior for Bob.

---

## 14. Developer Commands (Backend)

All commands run from `backend/`. The frontend has no build system yet.

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
cd backend && python -m pytest

# Run a single test by node ID
cd backend && python -m pytest tests/test_python_adapter.py::test_extract_nodes_from_fixture -v

# Run a single test file
cd backend && python -m pytest tests/test_xray_routes.py -v

# Lint (fix auto-fixable issues)
cd backend && python -m ruff check app/ tests/ --fix

# Format
cd backend && python -m black app/ tests/

# Check lint + format (CI mode, no writes)
cd backend && python -m ruff check app/ tests/ && python -m black --check app/ tests/
```

---

## 15. Non-Obvious Implementation Details (Discovered by Reading Code)

**DB engine is a module-level singleton in `app/db/evidence_store.py`.**
The global `_engine` variable is lazily initialised on first call to `get_engine()`. Tests MUST reset it between runs — `conftest.py` does this via `evidence_store._engine = None` in an `autouse` fixture. Any new test file that bypasses `conftest.py` will share state across tests and produce false passes.

**Every DB function accepts an optional `db_url` kwarg (default `sqlite:///./repodoc.db`).**
Integration tests pass an in-memory or `tmp_path`-scoped URL to stay isolated. Do not call store functions without specifying a test URL in test context.

**`adapter_registry.get_adapter(language)` takes a language string, NOT a repo path.**
`get_adapter_for_repo(repo_path)` is the path-based alternative. The xray route uses `get_adapter(stack["language"])` — calling `get_adapter_for_repo` would bypass stack detection.

**Bob integration always returns `None` today (stub).**
`app/bob/integration._call_bob` is a stub that logs a warning and returns `None`. All callers handle `None` gracefully. Do not add logic that assumes Bob will return data until the real interface is wired.

**`ruff.toml` excludes `tests/fixtures/syntax_error.py`** — this file is intentionally invalid Python and must not be parsed by any linter or formatter. Black will error on it; exclude it explicitly when formatting.

**`pytest.ini` sets `asyncio_mode = auto`** — all `async def` test functions run automatically without `@pytest.mark.asyncio`. Do not add that decorator; it is redundant and triggers a warning.

**Black line length is 88 (default); ruff line length is 100** — they differ. Black governs actual formatting. The ruff `line-length = 100` setting only prevents ruff from flagging long lines that black intentionally allows.

**`POST /api/v1/sessions/{id}/xray` returns 202, not 200.** The route is synchronous today (runs inline), but the 202 status is intentional — the spec describes it as an async trigger. Do not change this to 200.

**`TypeScriptAdapter.detect()` returns `True` for any repo containing `package.json`**, including Python repos that also have a frontend subfolder. The registry iterates `PythonAdapter` first, so Python wins when both markers exist. New adapters must be inserted *before* `TypeScriptAdapter` in `_REGISTRY`.

**Bob output is persisted even on failure (`parsed_ok=False`, empty `raw_output=""`).**
`_validate_and_store` always calls `evidence_store.save_bob_output` regardless of whether Bob returned data. This means every X-Ray run produces two `bob_outputs` rows. Do not add a guard that skips the insert on `None` — downstream queries rely on the presence of these rows to detect that agents were attempted.
