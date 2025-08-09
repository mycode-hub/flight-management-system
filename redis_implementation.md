# Redis Implementation Details

This document outlines the Redis data structures and caching strategy used in the flight management system. The design focuses on performance, data consistency, and memory efficiency by using appropriate Redis data structures and an event-driven cache invalidation approach.

## 1. Core Caching Strategy: Event-Driven Invalidation

Instead of relying on a simple Time-To-Live (TTL) for cache expiration, this system uses an **event-driven** model. This ensures that the cache is always consistent with the database.

-   **Cache Writes:** The cache is populated or updated whenever a flight is created, updated, or deleted via the Admin API. The API logic calls a dedicated `redis_service` to perform these updates atomically.
-   **Cache Invalidation:** When a flight is modified or deleted, the `redis_service` is responsible for finding and removing the old, stale entries from Redis.
-   **No TTL on Search Keys:** Search indexes (Sorted Sets) do not have a TTL. They are kept up-to-date by the application logic itself, providing a more reliable and accurate cache.

## 2. Redis Data Structures

We leverage three primary Redis data structures to create a highly efficient system.

### A. Flight Objects: Stored as Hashes

Each flight object is stored as a Redis **Hash**. This allows for granular control and memory-efficient storage.

-   **Key Format:** `flight:{flight_id}`
-   **Example Key:** `flight:a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`
-   **Value:** A hash where keys are the flight's attributes (e.g., `flight_number`, `price`) and values are their corresponding string representations.
-   **Benefit:** Allows for updating a single attribute (like `available_seats`) without rewriting the entire object. It is also highly readable for debugging.

### B. Search Indexes: Stored as Sorted Sets

To enable fast, server-side sorting and pagination, we use **Sorted Sets** to index flights.

-   **Key Format:** `search:{source}:{destination}:{date}:{sort_criteria}`
-   **Example Keys:**
    -   `search:New York:London:2025-09-15:price`
    -   `search:New York:London:2025-09-15:fastest`
-   **Score:** The value used for sorting.
    -   For the `:price` key, the score is the flight's `price`.
    -   For the `:fastest` key, the score is the flight's `departure_ts` (as a Unix timestamp).
-   **Member:** The `flight_id`.
-   **Benefit:** This is extremely powerful. The application can query Redis for a range of flight IDs already sorted by price or departure time, offloading this work from the database and the application itself.

### C. Seat Availability: Stored as Strings (Counters)

To prevent overbooking and handle high concurrency, a simple Redis **String** is used as an atomic counter for available seats.

-   **Key Format:** `flight_seats:{flight_id}`
-   **Example Key:** `flight_seats:a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11`
-   **Value:** An integer (stored as a string) representing the number of available seats.
-   **Benefit:** This allows for the use of atomic commands like `DECRBY` within a Redis transaction (`pipeline`), which is the core of the concurrency-safe booking logic.

## 3. Workflow Example: User Search

1.  A user requests `GET /search?source=New York&destination=London&date=2025-09-15&sort=price`.
2.  The application constructs the key: `search:New York:London:2025-09-15:price`.
3.  It uses `ZRANGE` on this key to get a list of the top N cheapest `flight_id`s.
4.  It then uses a pipeline to fetch the full flight data from the corresponding **Hashes** (`HGETALL flight:{flight_id}`) and the live seat counts from the **Counters** (`GET flight_seats:{flight_id}`).
5.  This data is combined and returned to the user.

This approach ensures that searches are fast, scalable, and always reflect the current state of the database.
