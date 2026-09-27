# Plan sharing

Lists finalized plans and shares one with a partner.

## Frontend

`App.jsx` (`/share`, `/planned-dates`) → `pages/SharePlan.jsx` → `/api/plan` and `/api/plan/share`

## Backend

`server.js` (`/api/plan/share`) → `modules/share/share.routes.js` → `share.controller.js` → `share.service.js`

Plan lookup belongs to [date planning](date-planning.md); the system notification belongs to [chat](chat.md).

