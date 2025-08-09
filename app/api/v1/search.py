from fastapi import APIRouter, Depends, Query, HTTPException
from app.schemas import schemas
from app.core.redis_client import get_redis
from typing import List
import redis
from datetime import date

router = APIRouter()

@router.get("/search", response_model=List[schemas.Flight])
def search_flights(
    source: str, 
    destination: str, 
    date: date, 
    sort: str = Query("price", enum=["price", "fastest"]),
    limit: int = 20,
    redis_client: redis.Redis = Depends(get_redis)
):
    # Determine the correct sorted set to use
    search_key = f"search:{source}:{destination}:{date}:{sort}"
    
    # Get a list of flight IDs from the sorted set
    # For 'price' and 'fastest' (departure time), lower scores are better.
    flight_ids = redis_client.zrange(search_key, 0, limit - 1)

    if not flight_ids:
        return []

    # Fetch the full flight details for each ID from the Hashes
    with redis_client.pipeline() as pipe:
        for flight_id in flight_ids:
            pipe.hgetall(f"flight:{flight_id.decode('utf-8')}")
        
        flight_hashes = pipe.execute()

    # Fetch the available seats for each flight
    with redis_client.pipeline() as pipe:
        for flight_id in flight_ids:
            pipe.get(f"flight_seats:{flight_id.decode('utf-8')}")
        
        available_seats_list = pipe.execute()

    # Combine the data into a list of Flight objects
    flights = []
    for i, flight_hash in enumerate(flight_hashes):
        if not flight_hash:
            continue
            
        # Decode hash values from bytes to string
        decoded_hash = {k.decode('utf-8'): v.decode('utf-8') for k, v in flight_hash.items()}
        
        # Add the live seat count
        available_seats = available_seats_list[i]
        decoded_hash['available_seats'] = int(available_seats) if available_seats else 0
        
        # Validate and create the Pydantic model
        try:
            print(f"DECODED HASH: {decoded_hash}")
            flights.append(schemas.Flight(**decoded_hash))
        except Exception as e:
            print(f"PYDANTIC ERROR: {e}")
            # This is a fallback for any data that might not have the timezone
            # In a real application, data cleaning and validation would be more robust
            try:
                decoded_hash['departure_ts'] = f"{decoded_hash['departure_ts']}+00:00"
                decoded_hash['arrival_ts'] = f"{decoded_hash['arrival_ts']}+00:00"
                flights.append(schemas.Flight(**decoded_hash))
            except Exception as e2:
                print(f"Could not parse flight data: {decoded_hash}, error: {e2}")
                continue

    return flights
