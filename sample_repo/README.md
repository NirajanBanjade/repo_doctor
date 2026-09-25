# sample_repo

This is the seeded demo repository used for the RepoDoc prototype.

## Contents (to be defined — see ARCHITECTURE.md §11 item 4)

The sample repository must contain:

- A FastAPI + PostgreSQL application.
- **2–3 deliberately seeded onboarding obstacles** (e.g., missing environment variable, wrong Python version pin, missing dependency).
- **One bounded starter task** defined in `tasks.json`.
- **One deliberately seeded downstream regression** — a changed function whose return value affects a known caller (e.g., a payment function whose return type change breaks an order-processing caller).

> **Open question:** The exact function names, file structure, regression location, and starter task specification are not yet defined. These must be decided before implementing the demo flow (AGENTS.md §11 Step 18).

## Structure (placeholder)

```
sample_repo/
├── app/          FastAPI application code
├── tests/        pytest test suite
├── tasks.json    StarterTask definition (see docs/api/contracts.md#StarterTask)
├── docker-compose.yml
└── README.md     (this file — will be replaced with a real README containing seeded obstacles)
```
