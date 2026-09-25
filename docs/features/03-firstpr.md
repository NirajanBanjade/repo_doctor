# Feature 03 — FirstPR

## Purpose

Give a new developer an immediate, low-risk contribution opportunity on the sample repository. FirstPR presents one predefined starter task, shows the precise code locations involved, guides the developer through the relevant code paths with repository-specific explanations, and connects the task directly to the impact and test features.

---

## Functional Requirements

1. Present a single predefined starter task sourced from the sample repository's specification (not discovered at runtime).
2. Display the task description, motivation, and the specific functions/files to change.
3. Invoke the Contribution Agent via Bob to generate a step-by-step implementation guide tailored to the repository's actual code.
4. Show the relevant code path: the target function, its immediate callers, and any tests that cover it.
5. Provide hints and explanations on demand without revealing the full solution immediately.
6. Link the starter task directly to ImpactScope so the developer can explore the task's impact radius before making changes.
7. Record the chosen task and any generated guidance in the session evidence store.

---

## Inputs

| Input | Source | Format |
|---|---|---|
| `session_id` | URL parameter | UUID |
| Predefined task definition | Static configuration in `sample_repo/tasks.json` | See `docs/api/contracts.md#StarterTask` |

---

## Outputs

| Output | Destination | Format |
|---|---|---|
| `ContributionGuidance` | SQLite `bob_outputs`, REST response | See `docs/api/contracts.md#ContributionGuidance` |
| Task implementation path | REST response | List of `{ node_id, description, hint }` |
| Linked ImpactScope entry point | REST response | `{ symbol_id, recommended_depth }` |

---

## Technical Implementation

### Task definition (`sample_repo/tasks.json`)

The starter task is defined statically. It specifies:

```json
{
  "id": "starter-task-001",
  "title": "...",
  "description": "...",
  "target_symbol": "module::function",
  "target_file": "relative/path.py",
  "target_line": 42,
  "recommended_impact_depth": 2
}
```

This file is committed alongside the sample repository. It is not generated at runtime.

### Contribution Agent invocation

Pass Bob: the task description, the target function's source code, its callers (from the existing dependency graph), and any existing test coverage for the target.

Validate response against `ContributionGuidance` schema: `steps[]`, `hints[]`, `caveats[]`, `relevant_tests[]`.

### Graph lookup

Look up the `target_symbol` from the existing graph (built by X-Ray). If the symbol is not found (e.g., because X-Ray has not run), return a `412 Precondition Failed` with message: "Repository X-Ray must complete before FirstPR."

---

## Dependencies on Other Features

| Feature | Dependency type |
|---|---|
| Session Management | Required |
| Repository X-Ray | Required — the graph must exist to resolve the target symbol |
| Bob Integration | Required for Contribution Agent; degrades to a task description without guidance |
| ImpactScope | Soft — a "Explore impact" button links to ImpactScope for the target symbol |

---

## Acceptance Criteria

1. The predefined starter task is displayed with its description and the exact file and line of the target function.
2. The Contribution Agent produces at least 3 ordered implementation steps referencing actual code in the sample repository.
3. The developer can request a hint at each step without being shown the full solution.
4. A "Explore impact" link navigates to ImpactScope pre-populated with the target symbol and `depth = 2`.
5. All guidance is stored in `bob_outputs` and survives a page refresh (retrieved from the session, not re-generated).
6. If the Contribution Agent is unavailable, the task description and target location are still shown.

---

## Testing Requirements

- Unit test: `ContributionGuidance` schema validation rejects a response with an empty `steps[]`.
- Unit test: Correct `412` response when graph does not contain the target symbol.
- Integration test: `GET /api/v1/sessions/{id}/firstpr` returns task definition and guidance for a session with a completed X-Ray.
- Integration test: Guidance is retrieved from `bob_outputs` on subsequent calls without re-invoking Bob.
