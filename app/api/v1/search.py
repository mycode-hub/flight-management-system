from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.schemas import schemas
from app.core.redis_client import get_redis
from typing import List
import redis
from datetime import date, timedelta
from app.api.dependencies import get_db
from app.models import models
import json

router = APIRouter()

@router.get("/search", response_model=List[schemas.FlightPath])
def search_flights(
    source: str, 
    destination: str, 
    date: date, 
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    redis_key = f"{source}-{destination}-{date.strftime('%Y-%m-%d')}"
    cached_paths = redis_client.get(redis_key)
    
    if not cached_paths:
        return []

    flight_paths_ids = json.loads(cached_paths)
    
    results = []
    for path_ids in flight_paths_ids:
        flights_in_path = db.query(models.Flight).filter(models.Flight.id.in_(path_ids)).all()
        
        # Ensure the order is the same as in the path_ids and all flights were found
        if len(flights_in_path) == len(path_ids):
            sorted_flights = sorted(flights_in_path, key=lambda f: path_ids.index(str(f.id)))
            total_price = sum(f.price for f in sorted_flights)
            results.append(schemas.FlightPath(flights=sorted_flights, total_price=total_price))

    return results


