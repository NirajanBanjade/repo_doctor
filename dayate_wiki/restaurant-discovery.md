# Restaurant discovery

Finds nearby, searched, and registered restaurants and loads their photos.

## Frontend

`App.jsx` (`/cafes`) → `pages/Cafes.jsx` → `hooks/useNearbyRestaurants.js` → `services/restaurantService.js`

## Backend

`server.js` (`/api/restaurants`) → `modules/restaurants/restaurant.routes.js` → `restaurant.controller.js` → `restaurant.service.js`

Selecting a restaurant exits to [date planning](date-planning.md).

