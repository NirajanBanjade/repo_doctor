# Accounts and profile

Handles user, business, and admin sign-in; registration; profile editing; and password changes.

## Frontend

`App.jsx` account routes → `components/Login.jsx`, `components/Register.jsx`, `pages/Profile.jsx` → `/api/user/*`

`components/ProtectedRoute.jsx` is the route-access boundary.

## Backend

`server.js` (`/api/user`) → `modules/auth/auth.routes.js` → `auth.controller.js` → `auth.service.js` → `user.model.js`

