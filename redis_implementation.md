# Redis Implementation Details

This document outlines the Redis data structures and caching strategy used in the flight management system. The design focuses on performance and data consistency by using a precomputation strategy combined with event-driven updates.

## 1. Core Caching Strategy: Precomputation with Event-Driven Updates

The system's performance relies on precomputing all possible direct and indirect flight paths and storing the top 20 cheapest results in Redis. This ensures that search queries are extremely fast, as they only need to read a single key from the cache.

-   **Precomputation:** A script (`app/scripts/precompute_flights.py`) is responsible for calculating all possible flight paths for each source, destination, and date. It sorts these paths by price and stores the top 20 cheapest paths in Redis.
-   **Event-Driven Updates:** To keep the cache consistent, the system uses a Redis Pub/Sub channel named `flight_updates`. When a flight is created, updated, or deleted through the Admin API, a message is published to this channel. A background worker listens for these messages and triggers a targeted recalculation of only the affected flight paths.
-   **Periodic Updates:** A daily cron job runs the precomputation script for all flights to ensure the cache is fully synchronized with the database, catching any potential inconsistencies.

## 2. Redis Data Structures

### A. Precomputed Flight Paths: Stored as JSON Strings

The core of the search optimization is storing the precomputed flight paths as a simple JSON string.

-   **Key Format:** `{source}-{destination}-{date}`
-   **Example Key:** `Nagpur-Goa-2025-08-28`
-   **Value:** A JSON-encoded string representing a list of flight paths. Each path is a list of flight IDs.
    ```json
    [["flight_id_1", "flight_id_2"], ["flight_id_3"]]
    ```
-   **Benefit:** This allows the search endpoint to retrieve all the necessary information with a single `GET` command, making it incredibly fast.

### B. Seat Availability: Stored as Strings (Counters)

To prevent overbooking and handle high concurrency, a simple Redis **String** is used as an atomic counter for available seats.

-   **Key Format:** `flight_seats:{flight_id}`
-   **Example Key:** `flight_seats:a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`
-   **Value:** An integer (stored as a string) representing the number of available seats.
-   **Benefit:** This allows for the use of atomic commands like `DECRBY` within a Redis transaction (`pipeline`), which is the core of the concurrency-safe booking logic.

### C. Pub/Sub for Updates

A Redis **Pub/Sub channel** is used to trigger event-driven updates.

-   **Channel Name:** `flight_updates`
-   **Message Format:** A JSON string containing the `source`, `destination`, and `date` of the flight that was changed.
-   **Benefit:** This decouples the API from the worker, allowing for an asynchronous and scalable update process.

## 3. Workflow Example: User Search

1.  A user requests `GET /search?source=Nagpur&destination=Goa&date=2025-08-28`.
2.  The application constructs the key: `Nagpur-Goa-2025-08-28`.
3.  It uses a single `GET` command to retrieve the JSON string of precomputed flight paths.
4.  The application parses the JSON and queries the database to get the full details for each flight ID in the paths.
5.  The results are formatted and returned to the user.

This approach ensures that searches are fast, scalable, and always reflect the most up-to-date precomputed data.