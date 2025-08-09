import redis
from app.models.models import Flight
from app.schemas import schemas
import json

def update_flight_in_redis(redis_client: redis.Redis, flight: Flight):
    """
    Creates or updates the necessary Redis entries for a given flight.
    - A Hash for the flight object.
    - Entries in Sorted Sets for searching by price and departure time.
    - A counter for available seats.
    """
    # Use a pipeline for atomic execution
    with redis_client.pipeline() as pipe:
        # 1. Store the main flight object as a Hash
        flight_key = f"flight:{flight.id}"
        flight_data = schemas.Flight.from_orm(flight).dict()
        # Convert complex types to strings for the hash
        for key, value in flight_data.items():
            if not isinstance(value, (str, int, float, bool)):
                flight_data[key] = str(value)
        
        pipe.hset(flight_key, mapping=flight_data)

        # 2. Add to Sorted Sets for searching
        search_key_price = f"search:{flight.source}:{flight.destination}:{flight.departure_ts.date()}:price"
        search_key_fastest = f"search:{flight.source}:{flight.destination}:{flight.departure_ts.date()}:fastest"
        
        pipe.zadd(search_key_price, {str(flight.id): float(flight.price)})
        pipe.zadd(search_key_fastest, {str(flight.id): flight.departure_ts.timestamp()})

        # 3. Set the initial seat availability counter
        seat_key = f"flight_seats:{flight.id}"
        # Only set the seats if the key doesn't exist to avoid overwriting during an update
        pipe.setnx(seat_key, flight.available_seats)
        
        pipe.execute()

def delete_flight_from_redis(redis_client: redis.Redis, flight: Flight):
    """
    Deletes all Redis entries associated with a flight.
    """
    with redis_client.pipeline() as pipe:
        # Delete the main hash
        pipe.delete(f"flight:{flight.id}")

        # Remove from sorted sets
        search_key_price = f"search:{flight.source}:{flight.destination}:{flight.departure_ts.date()}:price"
        search_key_fastest = f"search:{flight.source}:{flight.destination}:{flight.departure_ts.date()}:fastest"
        pipe.zrem(search_key_price, str(flight.id))
        pipe.zrem(search_key_fastest, str(flight.id))

        # Delete the seat counter
        pipe.delete(f"flight_seats:{flight.id}")

        pipe.execute()
