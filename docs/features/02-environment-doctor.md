# Feature 02 — Environment Doctor (Current Implementation)

## Purpose

Extract setup commands from repository documentation, execute them in bounded Docker
containers, persist each result, and allow an explicitly approved patch followed by
a full rerun.

## Implemented Flow

- `build_setup_plan` reads README setup/install sections and fenced shell blocks.
- `POST /api/v1/sessions/{id}/environment/run` executes the plan and stores a new
  `run_number`. With no commands it returns `no_steps` and a warning.
- Each step records command, status, exit code, stdout/stderr, and timestamps.
- The first failed step triggers the Environment Agent wrapper. Bob is currently
  unavailable, so no diagnosis is returned.
- `POST /environment/fix` requires `approval=true`, optionally applies unified diff
  content with `patch -p1`, and reruns the full plan.
- `GET /environment/checks` returns history; `GET /environment/status` returns the
  latest run in the shared frontend contract.

## Isolation and Status

Setup execution uses `repodoc-sandbox`, one CPU, 512 MB, no network, a read-only
repository mount, and per-step timeout handling. Statuses are `verified`, `failed`,
`blocked`, or `infrastructure_error`. Only a successful container run is verified.

## Current Limitations

- Documentation parsing is heuristic, not a complete shell/document parser.
- The fix route logs a failed `patch` command but currently continues to rerun setup.
- The status response does not retrieve a persisted Bob diagnosis.

## Tests

Backend tests cover setup-plan extraction, Docker result classification, route
persistence, empty plans, approval checks, and latest-run status responses.
