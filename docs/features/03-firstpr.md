# Feature 03 — FirstPR (Not Currently Implemented)

## Current State

FirstPR is not part of the active product flow. A `FirstPRView` component, a
`StarterTask` type, and a client request for `/firstpr/tasks` remain in the frontend,
but the application filters the tab out and FastAPI registers no FirstPR routes.
There is no Contribution Agent schema or wrapper in the backend.

## Required Before Re-enabling

1. Define the task source and persisted task/guidance contract.
2. Add backend routes and integration tests.
3. Decide whether guidance is deterministic, Bob-assisted, or both.
4. Add the missing Contribution Agent schema/wrapper only if Bob remains in scope.
5. Restore the tab and add frontend loading, empty, unavailable, and navigation tests.
6. Ensure “Explore impact” uses one of the implemented ImpactScope origins.

Until those steps are complete, documentation and UI must not represent FirstPR as
available.
