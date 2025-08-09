# Backend Functionality

This document provides a comprehensive overview of all functionalities available in the flight management system's backend API. It is intended for developers who need to understand and interact with the API endpoints.

---

## 1. Admin API (`/admin`)

The Admin API provides a suite of tools for managing flights in the system. All endpoints in this section are prefixed with `/admin`.

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

## 2. Flight Search API (`/api/v1/search`)

This is the primary endpoint for end-users to find available flights. It is highly optimized for performance using a Redis-first approach.

**Endpoint:** `GET /api/v1/search`

**Query Parameters:**

| Parameter     | Type    | Description                                      |
| :------------ | :------ | :----------------------------------------------- |
| `source`      | string  | The departure location.                          |
| `destination` | string  | The arrival location.                            |
| `date`        | string  | The desired date of travel (format: `YYYY-MM-DD`). |
| `sort`        | string  | (Optional) Sort criteria: `price` or `fastest`. Default: `price`. |
| `limit`       | integer | (Optional) Number of results to return. Default: `20`. |

**How it Works:** The search endpoint does **not** hit the database directly. Instead, it queries pre-built indexes (Redis Sorted Sets) to get a list of flight IDs already sorted by the desired criteria. It then fetches the complete flight details from Redis Hashes, ensuring a very fast response time.

---

## 3. Booking API (`/api/v1/booking`)

This endpoint handles the critical process of booking a flight.

### Current Implementation: Single-Phase Booking

The current implementation uses a simplified, single-phase booking process for immediate confirmation. It is designed to be highly concurrent and prevent overbooking.

**Endpoint:** `POST /api/v1/booking`

**Request Body:**

| Field       | Type    | Description                               |
| :---------- | :------ | :---------------------------------------- |
| `user_id`   | UUID    | The ID of the user making the booking.    |
| `flight_id` | UUID    | The ID of the flight to be booked.        |
| `seats`     | integer | The number of seats to book.              |

**Concurrency-Safe Workflow:**
1.  The system first checks if the requested flight exists in the Redis cache.
2.  It then uses a Redis transaction (`pipeline` with `WATCH`) to atomically check the number of available seats.
3.  If enough seats are available, it decrements the seat counter in Redis and updates the corresponding flight Hash. This entire operation is atomic, meaning it's safe from race conditions.
4.  Only after the Redis transaction succeeds does the system write the final booking record to the PostgreSQL database with a status of **`CONFIRMED`**.
5.  If the Redis transaction fails (e.g., because the seat count changed mid-operation), the request is rejected with a `409 Conflict` status, and the user is asked to try again.

### Planned Feature: Mock Payment Integration

To more realistically simulate a real-world scenario, a **Mock Payment Service** is planned. This will transform the booking process into a two-phase operation.

**Phase 1: Reserving the Seats**
1.  When a booking request is made, the system will reserve the seats using the same atomic Redis transaction.
2.  It will then create a booking record in the database with a status of **`PENDING`**.
3.  The system will then make an outbound call to the Mock Payment Service, sending the booking details.

**Phase 2: Handling the Payment Outcome**
1.  The Mock Payment Service will simulate a delay and a random success/failure outcome.
2.  It will then call back to our API on a dedicated endpoint (e.g., `POST /payment/callback`) with the result.
3.  **On Payment Success:** The booking status is updated from `PENDING` to **`CONFIRMED`**. The booking is now final.
4.  **On Payment Failure:** A critical **compensating action** is performed. The booking status is updated to **`FAILED`**, and the reserved seats are atomically returned to the available seat pool in Redis. This ensures that failed bookings do not result in "lost" inventory.