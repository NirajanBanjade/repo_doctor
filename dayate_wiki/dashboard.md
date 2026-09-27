# User dashboard

Summarizes the signed-in user and accessible plans.

## Frontend

`App.jsx` (`/dashboard`) → `pages/Dashboard.jsx` → `hooks/useDashboard.js` → `services/dashboardService.js` → Dashboard components

## Backend

Uses `/api/user/profile` from [accounts](accounts.md) and `/api/plan/list` from [date planning](date-planning.md). It has no dashboard-specific backend module.

