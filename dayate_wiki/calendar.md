# Calendar memories

Shows accessible plans and their chat images by date.

## Frontend

`App.jsx` (`/date-calendar`) → `pages/DateCalendar.jsx` → `/api/chat/calendar`

## Backend

`server.js` (`/api/chat/calendar`) → `modules/calendar/calendar.routes.js` → `calendar.controller.js` → `calendar.service.js`

The service reads from [date planning](date-planning.md) and [chat](chat.md); those features remain separately owned.

