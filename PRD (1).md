# RepoDoc — Product Requirements Document

## 1. Product Overview

**RepoDoc** turns an unfamiliar software repository into a guided path from first clone to first verified contribution. Using **IBM Bob 2.0**, it helps developers understand the codebase, establish a working environment, explore the potential impact of a proposed or actual change, and create and execute relevant tests before preparing a pull request.

**Primary user:** A new developer joining a huge codebase in a company.

**Core outcome:** A developer can understand essential architecture, run the application, see how far the change may affect connected code, and verify impacted behavior with evidence-backed tests.

## 2. Problem

On unfamiliar codebases, developers lose time understanding architecture, resolving incomplete setup instructions, and finding the right place to make changes. Even after locating a function, they may not know which callers or downstream components depend on its behavior. Static READMEs and generic AI summaries neither verify setup instructions nor reliably reveal the likely impact and regression-test scope of a proposed change.

## 3. MVP Scope

| Feature | Requirements | Output |
| --- | --- | --- |
| **Repository X-Ray** | Import the trusted sample repository; detect stack, entry points, key modules, and relationships; attach source-file references. | Interactive, evidence-linked architecture map and module summaries. |
| **Environment Doctor** | Read setup docs and configuration; run setup, startup, and existing tests in an isolated container; diagnose failures and recheck approved fixes. | Verified setup instructions, check results, and unresolved blockers. |
| **FirstPR** | Offer one predefined starter task; show relevant implementation paths and tests; guide the developer with explanations and hints. | Task-specific learning path and proposed code changes. |
| **ImpactScope** | Let a developer select a function or Git diff and optionally describe an intended change; trace direct and transitive **potential** dependents up to a configurable depth; show evidence for each edge and distinguish verified relationships from hypotheses. | Interactive impact-radius graph, source references, and prioritized affected-code/test list. |
| **Radius Test Generator** | From the selected impact radius and intended/actual change, identify existing tests and coverage gaps; propose focused regression tests for affected behaviors; after approval, generate and execute tests in the sandbox. | Existing-test recommendations, generated test patch, results per impacted component, and uncovered risks. |
| **Verification & Documentation** | Run task acceptance tests and appropriate existing/generated regression tests; report observed results; propose setup-documentation fixes and a PR summary. | Evidence-based verification report, test evidence, and documentation patch. |

**MVP Architecture:**
 Design OnboardIQ with a modular, language-agnostic architecture using language-specific adapters (Python AST for Python, TypeScript Compiler API for JavaScript/TypeScript, and extensible adapters for other languages). Each adapter converts source-code relationships into a unified dependency graph used by Repository X-Ray, ImpactScope, and the Test Generator. Initially implement and validate Python support, with Node.js and other languages planned for future expansion.

## 4. End-to-End User Flow

1. **Import:** Select the sample repository; detect its technology stack.
2. **Understand:** Bob examines code and documentation while RepoDoc builds a source-linked architecture map.
3. **Prepare:** Environment Doctor sets up and starts the project in Docker, runs smoke checks, and reports verified instructions or blockers.
4. **Plan contribution:** Choose the predefined starter task and explore the relevant code.
5. **Explore impact:** Select the function to change or provide a Git diff; optionally describe the planned change (for example, changing a payment function's return value). Set impact depth (direct callers, two hops, or three hops). Inspect potentially affected nodes and click each connection to see supporting file paths, line numbers, and relationship type.
6. **Generate targeted tests:** Choose all or a subset of affected nodes. RepoDoc maps existing tests, highlights untested affected behavior, and proposes regression tests tied to the change and impact graph. After developer approval, generate test files.
7. **Contribute and verify:** Make or approve changes; run existing, newly generated, and task acceptance tests. Inspect failures and unresolved risks; receive a draft PR summary and proposed documentation updates.

No code is merged or deployed automatically.

## 5. ImpactScope and Test Generation Requirements

### 5.1 Impact graph

- **Inputs:** Selected symbol or Git diff; optional natural-language description of the intended behavior change; impact radius depth of 1–3.
- **Graph direction:** Show *dependents of changed code* (e.g., direct callers followed by their callers), not just the functions the selected function calls. Allow inspection of other relationship types, but label direction clearly.
- **Graph nodes:** Function or module name, path, line range, depth from changed code, and associated tests where discoverable.
- **Graph edges:** Relationship type (such as direct call or import), exact source reference (file and line), and evidence status: **confirmed by static analysis**, **observed in an executed test** (only when instrumented), or **possible/inferred**.
- **What-if analysis:** Use the intended change to propose behavior-specific risks (e.g., return-type changes affecting callers). Label risks as hypotheses until tests or code evidence validate them.
- **Limits:** Show dynamic or unresolved calls as unknown rather than pretending the graph is exhaustive; clearly display the chosen depth and analysis scope.

### 5.2 Test generation within the impact radius

- Identify existing tests linked to the changed function and selected affected components; recommend which to run first.
- For each selected affected component, derive **behavioral test scenarios** from its usage of the changed function and the intended/actual code diff.
- Prefer extending existing tests and using current project fixtures/mocks. Propose new tests only where coverage gaps are identified.
- Show a **test plan before generating code**, including scenario, impacted component, source evidence, expected behavior, and proposed test location.
- Generate test code **only after developer approval**. Execute it alongside applicable existing tests and starter-task acceptance tests in the isolated environment.
- Present per-component status: covered and passed, covered and failed, unexecuted, or no suitable test yet. Record stdout/stderr and commands, and link each generated test back to its graph node(s).
- Never describe passing generated tests as proof that every affected component is safe. Report skipped nodes, inferred relationships, missing assertions, and untested behavior.

## 6. IBM Bob 2.0 Integration

IBM Bob must drive the **multi-step workflow**, not merely assist in building the app. Implement integration using the Bob features and interfaces actually available in the hackathon environment.

- **Agent mode:** Coordinate investigation, troubleshooting, impact analysis, test planning, and verification.
- **Parallel subagents:** Architecture Agent analyzes code structure while Documentation Agent reviews repository guidance; Impact Agent explores dependent code paths while Test Agent finds existing coverage and prepares regression scenarios.
- **Document understanding:** Interpret README, configuration, contribution guidelines, and test conventions.
- **Environment Agent:** Diagnose setup failures and verify approved corrections.
- **Contribution Agent:** Guide the starter task using repository-specific evidence.
- **Verification Agent:** Execute tests and reconcile observed results with acceptance criteria and stated impact risks.

Persist agent findings, source references, planned changes, approvals, executed commands, and test results. If Bob does not expose a required orchestration API, demonstrate its supported agent workflow explicitly and have the backend consume its structured outputs through a supported interface rather than inventing an integration.

## 7. Technical Stack

| Layer | Technology |
| --- | --- |
| Agentic workflow | IBM Bob 2.0 |
| Frontend | React, TypeScript, React Flow |
| Backend | Python, FastAPI |
| Repository analysis | Git, Python `ast`, targeted document and source parsing |
| Graph and traversal | NetworkX (directed call/dependency graph, breadth-first search to depth 1–3) |
| Test mapping and execution | Pytest, existing test discovery, generated test patches |
| Isolated execution | Docker / Docker Compose |
| Sample application | FastAPI, PostgreSQL, Pytest |
| Session and evidence storage | SQLite |

**Architecture:** React UI → FastAPI workflow service → repository parser, impact graph builder, and sandboxed test runner. IBM Bob coordinates agent investigations and generates proposed guidance/tests through supported integration points. SQLite stores findings, references, graph relationships, selected radius, approved patches, and execution evidence.

## 8. Safety and Reliability

- Execute only the approved sample repository in a disposable, resource-limited container. Do not run arbitrary or unreviewed scripts on the host.
- Prevent secret exposure; do not print or commit secret values.
- Require developer approval for generated or modified files and before executing newly generated tests.
- Every confirmed impact edge must reference concrete code evidence; distinguish static relationships, observed behavior, and AI-inferred hypotheses.
- Mark setup instructions **verified** only after a successful clean-environment run.
- Preserve the original repository; make proposed changes on a separate working branch or isolated copy.
- Expose analysis blind spots, failing tests, unexecuted tests, and uncertainty rather than promising exhaustive impact detection.

## 9. Demo and Success Metrics

Prepare the sample repository with **2–3 known onboarding obstacles**, **one bounded starter task**, and **one deliberately seeded downstream regression** (e.g., a changed payment return value affecting an order-processing caller) with known affected code paths.

**Demo:** Import → explore architecture → repair setup blockers → select starter task → inspect the function's 1–3-hop impact radius and click source evidence → approve generated tests for affected nodes → make the change → run tests → expose the seeded regression → review verification report and PR summary.

Measure:

- **Setup:** Successful clean-container startup, smoke checks, and number of seeded setup blockers detected.
- **Impact accuracy:** Confirmed affected code paths found / known affected code paths in the seeded scenario; report false-positive or unsupported edges separately.
- **Evidence quality:** Proportion of displayed confirmed edges with navigable, valid source references.
- **Test usefulness:** Affected components with executed relevant tests; seeded regression detected; generated tests that execute successfully and assert the intended behavior.
- **Productivity:** Compare time and manual investigation steps from clone to first tested contribution against a README-only and manual-impact-analysis baseline, when feasible.

Use measured values only. Separate automated checks from any small human usability study.

## 10. Out of Scope for MVP

- Arbitrary-language or enterprise-monorepo support.
- Full runtime tracing, complete dynamic-call resolution, and comprehensive cross-service impact prediction.
- Automatic discovery or autonomous completion of live GitHub issues.
- Generating large test suites across all transitive dependencies by default; developers select the radius and nodes.
- Persistent cross-developer knowledge, production deployment, autonomous merging, and unrestricted execution.

## 11. MVP Completion Criteria

The prototype succeeds when it analyzes the sample repository, displays an evidence-linked architecture map, reproduces a working environment, guides a starter contribution, visualizes a configurable **dependency impact radius with per-edge references**, recommends and **generates approved regression tests tied to selected impacted components**, runs those tests in isolation, detects the seeded downstream regression, and outputs a verification report and proposed documentation improvements.
