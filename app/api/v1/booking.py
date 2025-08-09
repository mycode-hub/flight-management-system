from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import schemas
from app.models import models
from app.core.database import get_db
from app.core.redis_client import get_redis
import redis

router = APIRouter()

@router.post("/booking", response_model=schemas.Booking)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    flight_key = f"flight:{booking.flight_id}"
    seat_key = f"flight_seats:{booking.flight_id}"

    # Check if flight exists in cache first
    if not redis_client.exists(flight_key):
        # Fallback to DB
        flight = db.query(models.Flight).filter(models.Flight.id == booking.flight_id).first()
        if not flight:
            raise HTTPException(status_code=404, detail="Flight not found")
    
    # Use a Redis transaction to handle the booking atomically
    with redis_client.pipeline() as pipe:
        try:
            # Watch the seat counter for changes
            pipe.watch(seat_key)
            
            available_seats_str = pipe.get(seat_key)
            if available_seats_str is None:
                # If seats aren't in redis, check DB (should be rare)
                flight = db.query(models.Flight).filter(models.Flight.id == booking.flight_id).one()
                available_seats = flight.available_seats
                pipe.set(seat_key, available_seats) # Set it for next time
            else:
                available_seats = int(available_seats_str)

            if available_seats < booking.seats:
                raise HTTPException(status_code=400, detail="Not enough seats available")
            
            # Start the transaction
            pipe.multi()
            
            # 1. Decrement the atomic seat counter
            pipe.decrby(seat_key, booking.seats)
            # 2. Decrement the seats in the flight Hash for consistency
            pipe.hincrby(flight_key, "available_seats", -booking.seats)
            
            pipe.execute()
        except redis.WatchError:
            # If another booking happened concurrently, abort and ask user to retry
            raise HTTPException(status_code=409, detail="Seat availability changed, please try again")

    # If Redis was successful, proceed with DB write
    db_booking = models.Booking(
        user_id=booking.user_id,
        flight_id=booking.flight_id,
        seats=booking.seats,
        status="CONFIRMED"
    )
    db.add(db_booking)
    
    # Also update the master DB record
    db.query(models.Flight).filter(models.Flight.id == booking.flight_id).update(
        {"available_seats": models.Flight.available_seats - booking.seats},
        synchronize_session=False
    )

    db.commit()
    db.refresh(db_booking)
    
    return db_booking
