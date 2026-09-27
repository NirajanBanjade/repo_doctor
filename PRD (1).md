# RepoDoc — Current Product Requirements

## 1. Product Summary

RepoDoc is a local developer-onboarding and change-analysis workspace. A developer
opens a repository, optionally supplies a Markdown feature wiki, inspects an
evidence-labelled architecture graph, explores a proposed change, reviews and
approves a test plan, runs tests in Docker, and receives a verification report.

This document describes the implementation as of September 2026 and replaces the
earlier aspirational MVP plan. Unimplemented items are listed as known gaps.

## 2. Goals and Boundaries

- Navigate an unfamiliar repository from features to source files.
- Tie architecture and impact claims to source or wiki evidence.
- Keep deterministic analysis usable without optional AI assistance.
- Require approval before generated tests are written or executed.
- Run repository tests outside the host process with bounded resources.
- Report uncertainty, missing tests, and infrastructure failures honestly.

RepoDoc does not merge, deploy, submit pull requests, or claim that passing generated
tests prove a change is safe.

## 3. Current User Flow

1. Enter a local repository path and, optionally, a feature-wiki directory.
2. Create a SQLite-backed session.
3. Run X-Ray. With a wiki, it is authoritative and produces file-level feature
   ownership and flow. Without one, a Python or JavaScript/TypeScript adapter builds
   a static graph.
4. Optionally run README-derived setup commands through Environment Doctor.
5. Start ImpactScope from exactly one symbol, feature, file, or Git diff and select a
   dependent-direction BFS depth from 1–3.
6. Select impacted nodes. RepoDoc maps existing pytest files and proposes a plan.
   Because Bob is currently unavailable, normal operation uses deterministic Python
   AST scenarios and conservative source-contract scenarios.
7. Refine, reject, or approve the plan. Approval writes generated files to the
   separate working copy.
8. Explicitly run the approved files and applicable existing tests in Docker.
9. Review the cached verification report and PR-summary draft. RepoDoc does not
   submit the summary.

## 4. Architecture-Wiki Contract

The optional wiki has one feature per `.md` page; `README.md` is only an index. Each
feature page needs a level-one title and may contain `## Frontend` and `## Backend`.

- Backtick-delimited file paths become feature-owned graph nodes.
- Arrow expressions (`file A` → `file B`) become documented `uses` edges.
- Links to other feature pages become cross-feature connections.
- Missing files and malformed pages produce warnings.
- A synthesized frontend/backend boundary is labelled `inferred`.

When supplied, the wiki replaces adapter output for that X-Ray run; the two sources
are not currently merged.

## 5. Evidence Model

| Label | Current meaning |
|---|---|
| `confirmed_static` | Found by a source adapter or explicitly documented by the user-designated authoritative wiki. |
| `inferred` | Unresolved/dynamic relationship, external dependency, inferred boundary, or agent hypothesis. |
| `observed_test` | Reserved for runtime-observed relationships; no current path promotes edges to it. |

## 6. Approval and Isolation

- The source repository is mounted read-only during test execution.
- Generated tests go only under
  `${REPODOC_WORKING_COPY:-./working_copy}/tests/generated/`.
- Approval is plan-level and persisted before files are generated.
- Approval and execution are separate API and UI actions.
- Missing generated files block execution.
- Docker runs with one CPU, 512 MB memory, no network, and a 120-second timeout.
- Infrastructure errors are distinct from assertion failures.
- Fix and documentation patches target the configured working copy.

## 7. Current Stack

| Area | Implementation |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Query, React Flow, Axios |
| Backend | Python 3.11+, FastAPI, Pydantic v2 |
| Analysis | Python `ast`, regex-based JavaScript/TypeScript adapter, NetworkX |
| Persistence | SQLite through SQLAlchemy Core |
| Sandbox | Docker, pytest, pytest-json-report |
| Optional AI | IBM Bob boundary with Pydantic schemas; transport is unwired |

## 8. Implemented Surface

- Local session creation and retrieval, including optional wiki validation.
- X-Ray, Python and lightweight JavaScript/TypeScript adapters, and wiki graphs.
- Feature-, file-, symbol-, and diff-origin impact analysis.
- README setup extraction and Docker-based environment runs.
- Existing pytest mapping and deterministic test planning fallback.
- Plan refinement, rejection/approval, file generation, isolated execution, and
  result retrieval.
- Evidence aggregation, fallback verification, documentation patch generation, and
  a human-review PR-summary draft.
- React views for import, X-Ray, environment, impact, plans, results, and verification.

## 9. Known Gaps

- `_call_bob` logs and returns `None`; every Bob-assisted feature uses a fallback.
- FirstPR UI code exists but is hidden, and no FirstPR backend routes are registered.
- No WebSocket route exists; the UI uses REST and React Query.
- Runtime coverage-to-edge correlation and `observed_test` promotion are absent.
- The JavaScript/TypeScript adapter uses regex parsing and creates only import edges.
- Formal Alembic migrations are absent; schema creation and a small compatibility
  upgrade are used instead.
- X-Ray retrieval returns `null` for agent findings even though attempts are stored.
- Verification `GET` creates the first report and PR-summary draft; there is no
  separate approval endpoint for summary creation.

## 10. Current Completion Standard

The implementation is coherent when backend tests pass, the frontend builds and its
approval tests pass, contracts match live routes, and the wiki/X-Ray → impact → plan
→ approve → run → verification flow works without representing Bob analysis or
runtime edge observation as available.
