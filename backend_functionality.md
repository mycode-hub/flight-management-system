# Backend Functionality

This document provides a comprehensive overview of all functionalities available in the flight management system's backend API. It is intended for developers who need to understand and interact with the API endpoints.

---

## 1. Authentication API (`/api/v1/auth`)

This API handles user registration and authentication.

| Method | Endpoint     | Description                                                                                             | Request Body Example                               |
| :----- | :----------- | :------------------------------------------------------------------------------------------------------ | :------------------------------------------------- |
| `POST` | `/register`  | Register a new user.                                                                                    | `{"username": "testuser", "password": "password123"}` |
| `POST` | `/token`     | Log in a user to receive a JWT access token. The token is required for all protected endpoints.         | `username=testuser&password=password123` (form-data) |

---

## 2. Admin API (`/admin`)

The Admin API provides a suite of tools for managing flights in the system. All endpoints in this section are prefixed with `/admin` and **require an admin-level JWT token for access**.

### Single Flight Management

These endpoints are for creating, viewing, updating, and deleting individual flights. Any action taken here triggers an immediate, event-driven update to the Redis cache to ensure data consistency.

| Method | Endpoint                  | Description                                     | Example Request Body                                                                                                                            |
| :----- | :------------------------ | :---------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/flights`                | Add a new flight to the system.                 | `{"flight_number": "AI-202", "source": "Delhi", "destination": "Mumbai", "departure_ts": "2025-12-25T10:00:00Z", "arrival_ts": "2025-12-25T12:00:00Z", "total_seats": 150, "price": 7500.00}` |
| `GET`  | `/flights/{flight_id}`    | Get details for a specific flight.              | (None)                                                                                                                                          |
| `PUT`  | `/flights/{flight_id}`    | Update an existing flight's details.            | (Same as POST body)                                                                                                                             |
| `DELETE`| `/flights/{flight_id}`    | Remove a flight from the system.                | (None)                                                                                                                                          |

### Bulk Flight Management

This feature allows an administrator to create or update multiple flights at once by uploading a CSV file. This is ideal for managing seasonal schedules or importing data from external systems.

The process is handled **asynchronously** to prevent HTTP timeouts with large files.

| Method | Endpoint                        | Description                                                                                                                                                           |
| :----- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/flights/bulk-upload`          | Upload a `text/csv` file to start the process. The API immediately returns a `job_id`. The CSV must have a header row matching the flight schema. |
| `GET`  | `/flights/bulk-upload/status/{job_id}` | Check the status of a background job. Returns the status (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`) and a summary of the results. |

**Upsert Logic:** The background job reads the CSV row by row and performs an "upsert" (update or insert) operation for each flight based on its `flight_number` and `departure_ts`. If the flight exists, it's updated; otherwise, it's created.

---

## 3. Flight Search API (`/api/v1/search`)

This is the primary endpoint for end-users to find available flights. It is highly optimized for performance using a Redis-first approach with precomputed flight paths.

**Endpoint:** `GET /api/v1/search`

**Query Parameters:**

| Parameter     | Type    | Description                                      |
| :------------ | :------ | :----------------------------------------------- |
| `source`      | string  | The departure location.                          |
| `destination` | string  | The arrival location.                            |
| `date`        | string  | The desired date of travel (format: `YYYY-MM-DD`). |

**How it Works:** The search endpoint queries Redis for a precomputed list of the top 20 cheapest flight paths (both direct and indirect). It then fetches the full flight details from the database and returns the combined results. This approach is extremely fast as all the complex pathfinding and sorting is done ahead of time.

---

## 4. Airports API (`/api/v1/airports`)

This endpoint provides a list of all unique airport locations available in the system.

**Endpoint:** `GET /api/v1/airports`

**Response:**
A JSON array of strings, where each string is an airport name.
```json
["Ahmedabad", "Bangalore", "Chennai", "Delhi", "Hyderabad", "Jaipur", "Kolkata", "Lucknow", "Mumbai", "Pune"]
```

---

## 5. Booking API (`/api/v1`)

This endpoint handles the critical process of booking a flight. **This endpoint requires a valid JWT token for access.**

### Current Implementation: Single-Phase Booking

The current implementation uses a simplified, single-phase booking process for immediate confirmation. It is designed to be highly concurrent and prevent overbooking.

| Method   | Endpoint                | Description                               | Request Body Example                               |
| :------- | :---------------------- | :---------------------------------------- | :------------------------------------------------- |
| `POST`   | `/booking`              | Creates a new booking for a flight.       | `{"flight_id": "flight-uuid", "seats": 2}`         |
| `GET`    | `/bookings`             | Gets a list of the current user's bookings. | (None)                                             |
| `DELETE` | `/bookings/{booking_id}`| Cancels a booking.                        | (None)                                             |

**Concurrency-Safe Workflow (Create Booking):**
1.  The system uses a Redis lock to ensure that only one booking process can run at a time for a given flight.
2.  It then uses a Redis transaction (`pipeline` with `WATCH`) to atomically check the number of available seats.
3.  If enough seats are available, it decrements the seat counter in Redis.
4.  A booking record is created in the PostgreSQL database with a status of `PENDING`.
5.  A mock payment service is called, which will randomly succeed or fail.
6.  If the payment succeeds, the booking status is updated to `CONFIRMED`. The `flight_id` is then published to a Redis Pub/Sub channel named `seat_updates`.
7.  If the payment fails, the booking status is updated to `FAILED`, and a compensating action is performed to atomically return the seats to Redis.

**Cancel Booking Workflow:**
1.  The system verifies that the booking exists and belongs to the authenticated user.
2.  It updates the booking status to `CANCELLED` in the database.
3.  It atomically increments the seat counter in Redis to make the seats available again.
4.  The `flight_id` is published to the `seat_updates` channel to trigger a database sync.

**Write-Back Caching:**
A dedicated background worker subscribes to the `seat_updates` channel. This worker accumulates the flight IDs and periodically (every 12 hours) updates the `available_seats` in the PostgreSQL `flights` table with the latest counts from Redis. This approach minimizes database writes and improves the performance of the booking endpoint.