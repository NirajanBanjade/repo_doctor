# Feature 06 — Verification and Documentation (Current Implementation)

## Purpose

Aggregate the latest session evidence into a cautious verification report,
documentation patch proposals, and a human-review PR-summary draft.

## Implemented Flow

`GET /api/v1/sessions/{id}/verification` returns the cached report when one exists.
On first access it requires an impact run and aggregates:

- impacted node IDs and change description;
- latest plan and component/per-test results when present;
- inferred graph nodes/edges relevant to the run;
- environment checks;
- feature-wiki scope and connected-feature context.

The Verification Agent wrapper is attempted. With Bob unavailable,
`build_fallback_report` deterministically lists component outcomes and unresolved
risks without claiming complete safety. The report is persisted.

Documentation gaps returned by an agent can produce unified-diff patch files under
`working_copy/docs/fixes/`. The original repository is not modified. The response
always includes a disclaimer that passing tests are not proof of safety.

## Current Limitations

- Fallback reports cannot invent documentation gaps, so patches are normally absent
  while Bob is unwired.
- The GET route creates both the report and PR-summary draft; there is no separate
  PR-summary approval endpoint.
- Cached responses do not currently reproduce the original `patch_paths` list.
- RepoDoc does not create, submit, merge, or deploy a pull request.

## Tests

Tests cover evidence aggregation, fallback status/risk reporting, documentation diff
generation, route prerequisites, persistence/caching, and unavailable/invalid Bob
outputs.
