# Feature 02 — Environment Doctor

## Purpose

Automatically verify that a new developer can reproduce the project's working environment by running the repository's setup process inside an isolated Docker container, diagnosing any failures, and confirming that approved fixes produce a clean startup.

---

## Functional Requirements

1. Read and parse the repository's setup documentation (README, docker-compose files, Makefiles, requirements files).
2. Execute the documented setup sequence inside a disposable, resource-limited Docker container.
3. Run smoke checks (import the app, execute a health-check endpoint, or run the minimal test suite) after setup.
4. On failure, invoke the Environment Agent via Bob to diagnose the root cause and propose a fix.
5. Present the diagnosis and proposed fix to the developer; require approval before applying.
6. After approval, apply the fix to the working copy and re-run the setup sequence to verify the correction.
7. Label each setup step as `verified`, `failed`, or `blocked` based on observed container output.
8. A step is labeled `verified` only after a successful clean-container run, never based on inference.
9. Record all commands, stdout, stderr, exit codes, and timestamps.

---

## Inputs

| Input | Source | Format |
|---|---|---|
| `session_id` | URL parameter | UUID |
| Setup documents | Repository working copy | Markdown, YAML, plain text |
| Approved fix patch | Developer approval response | `{ step_id, fix_description, patch_content }` |

---

## Outputs

| Output | Destination | Format |
|---|---|---|
| Per-step check results | SQLite `environment_checks`, REST response | See `docs/api/contracts.md#EnvironmentCheck` |
| `EnvironmentDiagnosis` | SQLite `bob_outputs`, REST response | See `docs/api/contracts.md#EnvironmentDiagnosis` |
| Container logs | SQLite `environment_checks.stdout/stderr` | Raw text |
| Verified setup instructions | REST response | Updated markdown with `[VERIFIED]` annotations |

---

## Technical Implementation

### Setup sequence builder (`app/services/environment_doctor.py`)

1. Parse README sections containing "setup", "install", "getting started", "prerequisites".
2. Extract ordered shell commands from fenced code blocks.
3. Generate a `SetupPlan`: an ordered list of `SetupStep(command, expected_exit_code, timeout_s)`.
4. Default `expected_exit_code = 0` for all steps unless the README specifies otherwise.

### Container lifecycle (`app/sandbox/docker_runner.py`)

- Build from `docker/Dockerfile.sandbox` if not already built for this session.
- Mount the working copy read-only at `/repo`.
- Apply resource limits: `--cpus=1`, `--memory=512m`, `--network=none` (or allow-listed pip/npm mirrors).
- Execute each `SetupStep` sequentially; capture stdout, stderr, and exit code.
- On step failure, stop the sequence and record `status = "failed"` for that step and `status = "blocked"` for all subsequent steps.
- Container is removed after each run (not reused between attempts).

### Environment Agent invocation

- Pass Bob the Environment Agent: failed step command, its stdout/stderr, the relevant README section, and the repository's language/framework.
- Validate response against `EnvironmentDiagnosis` schema.
- `EnvironmentDiagnosis` includes: `root_cause`, `proposed_fix` (human-readable), `patch` (optional file diff), `confidence`.

### Re-verification

- After developer approves and the fix is applied to the working copy, re-run the full setup sequence from the beginning in a fresh container.
- Record the new run results; compare `verified` steps before and after.

---

## Dependencies on Other Features

| Feature | Dependency type |
|---|---|
| Session Management | Required |
| Docker Sandbox Runner | Required — all execution happens in the sandbox |
| Repository X-Ray | Soft dependency — stack detection informs the setup parser |
| Bob Integration | Required for Environment Agent; degrades to raw failure display if unavailable |

---

## Acceptance Criteria

1. Given the sample repository with 2–3 seeded setup blockers, Environment Doctor detects all of them as `failed` steps.
2. The Environment Agent proposes a correct fix for each seeded blocker.
3. After all approved fixes are applied and the sequence re-runs, all steps are labeled `verified`.
4. No host-side commands are executed; all setup runs happen inside the Docker sandbox.
5. Container stdout and stderr for every step are stored verbatim and visible in the UI.
6. A step is never labeled `verified` unless its exit code matched `expected_exit_code` in a clean container run.
7. A run that exceeds the container timeout (120 s) is reported as `infrastructure_error`, not as a step failure.
8. The developer must explicitly approve each proposed fix before it is applied; no fix is applied automatically.

---

## Testing Requirements

- Unit test: Setup plan builder correctly extracts commands from README fixtures with various code block styles.
- Unit test: `EnvironmentDiagnosis` schema validation rejects a response missing `root_cause`.
- Integration test: `POST /api/v1/sessions/{id}/environment/run` triggers a Docker run and returns step results.
- Integration test: `POST /api/v1/sessions/{id}/environment/fix` requires `approval = true`; returns 400 if not present.
- Sandbox test: A container run that exceeds the timeout is recorded as `infrastructure_error`.
- Sandbox test: A step with exit code 1 correctly marks subsequent steps as `blocked`.
