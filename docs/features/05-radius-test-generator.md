# Feature 05 — Test Planning, Generation, and Execution

## Purpose

Turn selected impact nodes into an evidence-backed plan, require plan-level approval
before writing files, and require a separate action before isolated execution.

## Plan Creation

`POST /api/v1/sessions/{id}/tests/plan` accepts an impact run and a non-empty subset
of its nodes. It validates ownership, returns an existing plan for that impact run
when present, maps existing pytest files, and calls the Test Agent wrapper.

When Bob is unavailable, `deterministic_test_planner.py` derives scenarios from
Python AST evidence:

- normal path;
- explicit conditional branches;
- explicit `raise` paths;
- decorated FastAPI route contracts;
- source contracts for unsupported or file-level nodes.

The plan includes rationale, notes, existing mappings, coverage gaps, selected nodes,
and connected-feature suggestions. `POST .../{plan_id}/refine` may update only a
`proposed` plan; with Bob unavailable it preserves the current scenarios.

## Approval and Generation

`POST .../{plan_id}/approve` accepts `{plan_id, approved}`. Rejection changes status
without writing files. Approval changes status to `approved`, generates conservative
pytest source-contract files under the configured working copy, and records
`generation_status` and `generated_test_file` in scenario JSON.

Approval is the file-writing gate. It does not execute tests.

## Execution

`POST .../{plan_id}/run` requires approved status and existing generated files. It
reruns test mapping, then sends applicable existing tests and generated tests to the
Docker executor. The source and working-copy mounts are read-only; the container has
one CPU, 512 MB, no network, and a 120-second timeout.

Pytest JSON results map back to components as `covered_passed`, `covered_failed`,
`unexecuted`, or `no_suitable_test`. Infrastructure failures remain distinct from
test failures. Session-level and plan-level GET routes retrieve results.

## Honesty Requirements

Generated source-contract checks do not establish business correctness. Responses
must expose unexecuted/no-test components, inferred edges, and scope limitations.

## Tests

Tests cover deterministic planning, mapping, schemas, idempotent plan retrieval,
refinement constraints, plan-level approval/rejection, generated-file metadata,
missing-file rejection, executor parsing, and component statuses.
