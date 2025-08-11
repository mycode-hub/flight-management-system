#!/bin/bash
docker compose exec -e PYTHONPATH=. api python3 app/scripts/precompute_flights.py
