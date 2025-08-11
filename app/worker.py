import time
import redis
from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models import models
from app.core.redis_client import get_redis
import threading
import subprocess
import json

# Set up the database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# In-memory set to store flight IDs that need updating
FLIGHTS_TO_UPDATE = set()
FLUSH_INTERVAL = 43200  # 12 hours in seconds

def run_precomputation(source, destination, date):
    """Runs the precomputation script for a specific route and date."""
    try:
        command = [
            "python3", "app/scripts/precompute_flights.py",
            "--source", source,
            "--destination", destination,
            "--date", date
        ]
        subprocess.run(command, check=True)
        print(f"Successfully precomputed flights for {source}-{destination} on {date}")
    except subprocess.CalledProcessError as e:
        print(f"Error during precomputation for {source}-{destination} on {date}: {e}")

def flight_update_subscriber():
    """
    Subscribes to the 'flight_updates' Redis channel and triggers
    precomputation for affected flight paths.
    """
    pubsub = get_redis().pubsub()
    pubsub.subscribe("flight_updates")
    
    print("Listening for flight updates...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            source = data['source']
            destination = data['destination']
            date = data['date']
            
            print(f"Received flight update for {source}-{destination} on {date}. Triggering precomputation.")
            # In a production system, you'd likely use a proper task queue like Celery
            threading.Thread(target=run_precomputation, args=(source, destination, date)).start()

def flush_updates_to_db():
    """
    This function runs in a separate thread and periodically flushes the
    accumulated flight ID updates to the database.
    """
    db = SessionLocal()
    while True:
        time.sleep(FLUSH_INTERVAL)
        
        if not FLIGHTS_TO_UPDATE:
            continue

        try:
            # Create a copy of the set to avoid issues with concurrent modification
            flight_ids_to_process = FLIGHTS_TO_UPDATE.copy()
            FLIGHTS_TO_UPDATE.clear()

            for flight_id in flight_ids_to_process:
                seat_key = f"flight_seats:{flight_id}"
                available_seats = get_redis().get(seat_key)
                
                if available_seats is not None:
                    db.query(models.Flight).filter(models.Flight.id == flight_id).update(
                        {"available_seats": int(available_seats)},
                        synchronize_session=False
                    )
            
            db.commit()
            print(f"Successfully flushed {len(flight_ids_to_process)} flight(s) to the database.")

        except Exception as e:
            print(f"Error during database flush: {e}")
            db.rollback()

def seat_update_subscriber():
    """
    This function subscribes to the 'seat_updates' Redis channel and adds
    flight IDs to the in-memory set.
    """
    pubsub = get_redis().pubsub()
    pubsub.subscribe("seat_updates")
    
    print("Listening for seat updates...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            flight_id = message['data'].decode('utf-8')
            FLIGHTS_TO_UPDATE.add(flight_id)
            print(f"Received update for flight: {flight_id}. Total pending updates: {len(FLIGHTS_TO_UPDATE)}")

if __name__ == "__main__":
    # Start the database flush thread
    flush_thread = threading.Thread(target=flush_updates_to_db, daemon=True)
    flush_thread.start()
    
    # Start the flight update subscriber thread
    flight_update_thread = threading.Thread(target=flight_update_subscriber, daemon=True)
    flight_update_thread.start()
    
    # Start the Redis subscriber
    seat_update_subscriber()