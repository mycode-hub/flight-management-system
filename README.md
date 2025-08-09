# Real-Time Flight Management System

This project is a production-ready, real-time backend and frontend for a flight management and booking system. It is built with Python, FastAPI, and React, designed to handle flight searches, bookings, and administration with high concurrency and reliability.

## Key Features

*   **Admin API:** Endpoints for adding, updating, and deleting flights.
*   **Flight Search:** A fast, cached search endpoint to find flights by source, destination, and date.
*   **Airport Autosuggest:** An endpoint to provide a list of available airports for search suggestions.
*   **Concurrent Booking:** A booking system that safely handles concurrent requests and prevents overbooking by using Redis for atomic seat management.
*   **Scalable Architecture:** Built on a containerized architecture with Docker, allowing the system to be easily scaled.
*   **Extensible:** Designed to be extensible with features like real-time notifications and mock payment services.

## Tech Stack

*   **Backend:** Python 3.11, FastAPI
*   **Frontend:** React, TypeScript
*   **Database:** PostgreSQL 15
*   **Cache:** Redis 7
*   **Containerization:** Docker & Docker Compose

## Prerequisites

Before you begin, ensure you have the following installed on your system:
*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Getting Started

Follow these steps to get the application up and running on your local machine.

**1. Clone the repository:**
```bash
git clone <repository-url>
cd flight-management-system
```

**2. Build and run the application:**
This command will build the Docker images and start the `api`, `frontend`, `postgres`, and `redis` services in detached mode.

```bash
docker compose up --build -d
```

The application will be available at `http://localhost:3000`. The API is available at `http://localhost:8000`.

You can check the logs to ensure all services are running correctly:
```bash
docker compose logs -f
```

**3. Stopping the application:**
To stop and remove the containers, run:
```bash
docker compose down
```

## API Endpoints

The application exposes the following REST API endpoints.

### Admin

| Method | Endpoint                                   | Description                                     | Request Body Example                                                                                                                            |
| :----- | :----------------------------------------- | :---------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST` | `/admin/flights`                           | Add a new flight.                               | `{"flight_number": "AI-202", "source": "Delhi", "destination": "Mumbai", "departure_ts": "2025-12-25T10:00:00Z", "arrival_ts": "2025-12-25T12:00:00Z", "total_seats": 150, "price": 7500.00}` |
| `POST` | `/admin/flights/bulk-upload`               | Bulk upload flights from a CSV file.            | (multipart/form-data)                                                                                                                           |
| `GET`  | `/admin/flights/bulk-upload/status/{job_id}` | Get the status of a bulk upload job.            | (None)                                                                                                                                          |
| `GET`  | `/admin/flights/{flight_id}`               | Get details for a specific flight.              | (None)                                                                                                                                          |
| `PUT`  | `/admin/flights/{flight_id}`               | Update an existing flight's details.            | (Same as POST body)                                                                                                                             |
| `DELETE`| `/admin/flights/{flight_id}`               | Remove a flight from the system.                | (None)                                                                                                                                          |

### Search

| Method | Endpoint         | Description                                                                                                                                                           | Query Parameters                                                                                             |
| :----- | :--------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/search` | Searches for flights. Results are cached in Redis for 300 seconds. | `source` (str), `destination` (str), `date` (str), `sort` (str, optional: "price" or "fastest"), `limit` (int, optional) |

### Airports

| Method | Endpoint           | Description                                      |
| :----- | :----------------- | :----------------------------------------------- |
| `GET`  | `/api/v1/airports` | Returns a list of all unique airport locations. |

### Booking

| Method | Endpoint          | Description                                                                                                                                                           | Request Body Example                               |
| :----- | :---------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------- |
| `POST` | `/api/v1/booking` | Creates a new booking. Uses Redis transactions to prevent overbooking. | `{"user_id": "user-uuid", "flight_id": "flight-uuid", "seats": 2}` |

## Folder Structure

The project is organized to separate concerns and maintain a clean codebase.

```
/
├───.gitignore              # Specifies files for Git to ignore
├───docker-compose.yml      # Defines and orchestrates the multi-container Docker application
├───Dockerfile              # Instructions to build the Docker image for the FastAPI application
├───requirements.txt        # Lists the Python packages required for the project
├───README.md               # Project overview and instructions
├───frontend/               # Frontend React application
└───app/                    # Main directory for all application source code
    ├───main.py             # Entry point of the FastAPI application
    ├───api/
    │   └───v1/             # API endpoint logic (controllers)
    │       ├───admin.py    # Endpoints for administrative tasks
    │       ├───search.py   # Endpoint for searching flights
    │       └───booking.py  # Endpoint for creating bookings
    ├───core/               # Core application logic and configuration
    │   ├───database.py     # Database connection and session management
    │   └───redis_client.py # Redis server connection
    ├───models/             # Database table structures (SQLAlchemy models)
    │   └───models.py       # `flights` and `bookings` table models
    └───schemas/            # Data shapes for API requests/responses (Pydantic models)
        └───schemas.py      # Pydantic models for data validation
```

## Future Work

This project is under active development. Future milestones include:
*   **Mock Payment Service:** Implementing a mock payment service to simulate real-world payment flows.
*   **Testing:** Adding comprehensive unit, integration, and load tests.
*   **Observability:** Integrating Prometheus for metrics and OpenTelemetry for tracing.
*   **CI/CD:** Setting up a full CI/CD pipeline with GitHub Actions.