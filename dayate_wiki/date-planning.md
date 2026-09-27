# Date planning

Creates a restaurant-based draft, then lists, finalizes, edits, or deletes plans.

## Frontend

`App.jsx` (`/cafes/:id`, `/my-plans`) → `pages/CafeReservation.jsx`, `pages/MyPlans.jsx` → `/api/plan/*`

## Backend

`server.js` (`/api/plan`) → `modules/plans/plan.routes.js` → `plan.controller.js` → `plan.service.js` / `plan.model.js`

Starts after [restaurant discovery](restaurant-discovery.md). Sharing and chat are separate features.

