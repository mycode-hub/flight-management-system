# Implementation Prompt — Real-Time Flight Management System (End-to-End)

**Purpose:**  
Build a production-ready, real-time flight management and booking system. This document provides a comprehensive guide to implementing the entire system, including the backend, frontend, database, and infrastructure.

---

# 1. Project Overview

The system is a full-stack application that allows users to search for flights, view results, and book seats. It also includes an admin interface for managing flights, including a bulk upload feature. The application is designed to be highly concurrent, reliable, and scalable.

## 1.1. Core Technologies

*   **Backend:** Python 3.11, FastAPI
*   **Frontend:** React, TypeScript
*   **Database:** PostgreSQL 15
*   **Cache:** Redis 7
*   **Containerization:** Docker & Docker Compose

---

# 2. System Architecture

The application is composed of four main services that are orchestrated with Docker Compose:

1.  **Backend API (`api`):** A FastAPI application that handles all business logic, including flight searches, bookings, and administrative tasks.
2.  **Frontend (`frontend`):** A React application that provides the user interface for searching, booking, and managing flights.
3.  **Database (`postgres`):** A PostgreSQL database that serves as the persistent storage for all flight and booking data.
4.  **Cache (`redis`):** A Redis instance that is used for caching flight data for fast searches and for managing seat availability to prevent overbooking.

---

# 3. Database Schema

The database consists of three main tables: `flights`, `bookings`, and `users`.

## 3.1. `flights` Table

```sql
CREATE TABLE flights (
  id UUID PRIMARY KEY,
  flight_number TEXT,
  source TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_ts TIMESTAMP WITH TIME ZONE NOT NULL,
  arrival_ts TIMESTAMP WITH TIME ZONE,
  total_seats INT NOT NULL,
  available_seats INT NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  version BIGINT DEFAULT 1,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## 3.2. `bookings` Table

```sql
CREATE TABLE bookings (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  flight_id UUID REFERENCES flights(id),
  seats INT NOT NULL,
  status TEXT NOT NULL, -- PENDING, CONFIRMED, CANCELLED, FAILED
  payment_ref TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## 3.3. `users` Table

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  is_admin BOOLEAN DEFAULT FALSE
);
```

---

# 4. Backend Implementation

The backend is a FastAPI application with the following structure:

```
app/
├───main.py
├───api/
│   └───v1/
│       ├───admin.py
│       ├───booking.py
│       ├───search.py
│       ├───airports.py
│       └───auth.py
├───core/
│   ├───database.py
│   ├───redis_client.py
│   └───security.py
├───models/
│   └───models.py
└───schemas/
    └───schemas.py
```

## 4.1. API Endpoints

### Authentication (`/api/v1/auth`)

*   `POST /register`: Registers a new user.
*   `POST /token`: Logs in a user and returns a JWT token.

### Admin (`/admin`)

*   `POST /admin/flights`: Adds a new flight to the system.
*   `POST /admin/flights/bulk-upload`: Bulk uploads flights from a CSV file.
*   `GET /admin/flights/bulk-upload/status/{job_id}`: Checks the status of a bulk upload job.

### Search (`/api/v1`)

*   `GET /api/v1/search`: Searches for flights based on source, destination, and date.
*   `GET /api/v1/airports`: Returns a list of all unique airport locations.

### Booking (`/api/v1`)

*   `POST /api/v1/booking`: Creates a new booking for a flight.

---

# 5. Frontend Implementation

The frontend is a React application with the following structure:

```
frontend/
├───public/
└───src/
    ├───components/
    │   ├───FlightResults.tsx
    │   ├───Header.tsx
    │   ├───SearchForm.tsx
    │   └───PrivateRoute.tsx
    ├───pages/
    │   ├───AdminPage.tsx
    │   ├───BookingPage.tsx
    │   ├───HomePage.tsx
    │   ├───LoginPage.tsx
    │   └───RegisterPage.tsx
    ├───services/
    │   └───api.ts
    └───types/
        └───index.ts
```

## 5.1. Key Components

*   **`SearchForm.tsx`:** Provides the UI for searching for flights, including autosuggestions for the source and destination.
*   **`FlightResults.tsx`:** Displays the results of a flight search.
*   **`AdminPage.tsx`:** Provides a UI for adding single flights and for bulk uploading flights from a CSV file.
*   **`LoginPage.tsx` & `RegisterPage.tsx`:** Handle user authentication.
*   **`PrivateRoute.tsx`:** A component that protects routes from unauthenticated access.

---

# 6. Infrastructure and Deployment

The entire application is containerized and managed with Docker Compose.

## 6.1. `docker-compose.yml`

```yaml
services:
  api:
    build: .
    container_name: flight_api
    ports:
      - "8000:8000"
    volumes:
      - ./app:/code/app
    environment:
      - DATABASE_URL=postgresql://user:password@postgres:5432/flights
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: flights
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

volumes:
  postgres_data:
```

## 6.2. Backend `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /code/app
COPY flights.csv .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

## 6.3. Frontend `Dockerfile`

```dockerfile
# Use an official Node.js runtime as a parent image
FROM node:18-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package*.json ./

# Install any needed packages
RUN npm install

# Bundle app source
COPY . .

# Creates a build directory with a production build
RUN npm run build

# Use a smaller, more secure image for serving the build
FROM nginx:stable-alpine
COPY --from=0 /app/build /usr/share/nginx/html
RUN chown -R nginx:nginx /usr/share/nginx/html

# Expose port 80 and start nginx
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

# 7. Initial Data

The application is seeded with an initial dataset of 1,000 flights from the `flights.csv` file. This file is copied into the backend container and can be loaded into the database using the bulk upload feature.

---

# 8. Getting Started

1.  **Clone the repository.**
2.  **Build and run the application:**
    ```bash
    docker compose up --build -d
    ```
3.  **Access the application:**
    *   Frontend: `http://localhost:3000`
    *   Backend API: `http://localhost:8000`
4.  **Register an admin user:**
    *   Register a new user at `http://localhost:3000/register`.
    *   Manually set the `is_admin` flag for the new user in the database:
        ```bash
        docker compose exec postgres psql -U user -d flights -c "UPDATE users SET is_admin = true WHERE username = '<your-username>';"
        ```
5.  **Load the initial data:**
    *   Log in as the admin user.
    *   Use the bulk upload UI on the admin page (`http://localhost:3000/admin`) to upload the `flights.csv` file.
    *   Alternatively, use the following `curl` command:
        ```bash
        curl -X POST -H "Authorization: Bearer <your-token>" -F "file=@flights.csv;type=text/csv" http://localhost:8000/admin/flights/bulk-upload
        ```
