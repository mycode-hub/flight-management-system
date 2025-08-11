import json
import os
from collections import defaultdict
from datetime import datetime
from functools import partial
from concurrent.futures import ProcessPoolExecutor

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from app.core.config import settings
from app.models.models import Flight

def get_db_session():
    """Creates a new database session."""
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

def get_redis_client():
    """Creates a new Redis client."""
    return redis.from_url(settings.REDIS_URL)

def find_paths(flights_by_date, src, dst, date):
    """Finds all possible flight paths for a given source, destination, and date."""
    graph = defaultdict(list)
    for flight in flights_by_date.get(date, []):
        graph[flight.source].append(flight)

    all_paths = []
    stack = [(src, [])]

    while stack:
        current_airport, path = stack.pop()

        if current_airport == dst:
            all_paths.append(path)
            continue

        if len(path) >= 5:
            continue

        for flight in graph.get(current_airport, []):
            if flight.id not in {f.id for f in path}:
                new_path = path + [flight]
                stack.append((flight.destination, new_path))
    return all_paths

def calculate_path_price(path):
    """Calculates the total price of a flight path."""
    return sum(flight.price for flight in path)

def process_combination(combo, flights_by_date):
    """
    Worker function to find and sort paths for a single combination.
    Returns a tuple of (redis_key, redis_value) or None.
    """
    date, src, dst = combo
    paths = find_paths(flights_by_date, src, dst, date)

    if not paths:
        return None

    paths.sort(key=calculate_path_price)
    top_20_paths = paths[:20]

    if top_20_paths:
        redis_key = f"{src}-{dst}-{date.strftime('%Y-%m-%d')}"
        redis_value = json.dumps([[str(flight.id) for flight in path] for path in top_20_paths])
        return (redis_key, redis_value)
    
    return None
    
    return None

import argparse

def precompute_and_store_flights(specific_source=None, specific_destination=None, specific_date=None):
    """
    Fetches flight data and uses a process pool to precompute
    flight paths in parallel, then stores them in Redis.
    """
    db = get_db_session()
    all_flights = db.query(Flight).all()
    db.close()

    flights_by_date = defaultdict(list)
    for flight in all_flights:
        flights_by_date[flight.departure_ts.date()].append(flight)

    if specific_source and specific_destination and specific_date:
        combinations = [
            (datetime.strptime(specific_date, '%Y-%m-%d').date(), specific_source, specific_destination)
        ]
    else:
        unique_airports = {f.source for f in all_flights} | {f.destination for f in all_flights}
        unique_dates = flights_by_date.keys()

        combinations = [
            (date, src, dst)
            for date in unique_dates
            for src in unique_airports
            for dst in unique_airports
            if src != dst
        ]

    num_processes = os.cpu_count()
    print(f"Starting path precomputation with {num_processes} processes for {len(combinations)} combinations...")

    worker_func = partial(process_combination, flights_by_date=flights_by_date)

    results = []
    with ProcessPoolExecutor(max_workers=num_processes) as executor:
        results = list(tqdm(executor.map(worker_func, combinations), total=len(combinations)))

    print("Path precomputation finished. Storing results in Redis...")
    redis_client = get_redis_client()
    for result in tqdm(results):
        if result:
            redis_key, redis_value = result
            redis_client.set(redis_key, redis_value)

    print("All paths stored in Redis.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Precompute flight paths.")
    parser.add_argument("--source", help="Source airport")
    parser.add_argument("--destination", help="Destination airport")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format")
    args = parser.parse_args()

    precompute_and_store_flights(args.source, args.destination, args.date)