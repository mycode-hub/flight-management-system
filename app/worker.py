import time
import redis
from sqlalchemy.orm import sessionmaker
from app.core.database import engine
from app.models import models
from app.core.redis_client import get_redis
import threading

# Set up the database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# In-memory set to store flight IDs that need updating
FLIGHTS_TO_UPDATE = set()
FLUSH_INTERVAL = 43200  # 12 hours in seconds

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
    
    # Start the Redis subscriber
    seat_update_subscriber()
