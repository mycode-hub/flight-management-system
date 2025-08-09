from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import schemas
from app.models import models
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.redis_lock import RedisLock
from app.api.dependencies import get_current_user
from uuid import UUID
import redis
import random
import time
import uuid

router = APIRouter()

def mock_payment_service(booking_id: UUID, force_failure: bool = False):
    """
    Simulates a call to a payment service.
    - Introduces a random delay.
    - Randomly succeeds or fails.
    """
    time.sleep(random.uniform(0.5, 3))  # Simulate network latency
    if force_failure or random.random() < 0.2:  # 20% chance of failure
        return {"status": "FAILED", "payment_ref": f"ref_{uuid.uuid4()}"}
    return {"status": "SUCCESS", "payment_ref": f"ref_{uuid.uuid4()}"}

@router.post("/booking", response_model=schemas.Booking)
def create_booking(booking: schemas.BookingCreate, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis), current_user: models.User = Depends(get_current_user), force_payment_failure: bool = False):
    flight_key = f"flight:{booking.flight_id}"
    seat_key = f"flight_seats:{booking.flight_id}"
    lock_key = f"lock:flight:{booking.flight_id}"

    with RedisLock(redis_client, lock_key):
        # Use a Redis transaction to reserve the seats
        with redis_client.pipeline() as pipe:
            try:
                pipe.watch(seat_key)
                available_seats_str = pipe.get(seat_key)
                if available_seats_str is None:
                    raise HTTPException(status_code=404, detail="Flight data not found in cache.")
                
                available_seats = int(available_seats_str)
                if available_seats < booking.seats:
                    raise HTTPException(status_code=400, detail="Not enough seats available")

                pipe.multi()
                pipe.decrby(seat_key, booking.seats)
                pipe.hincrby(flight_key, "available_seats", -booking.seats)
                pipe.execute()
            except redis.WatchError:
                raise HTTPException(status_code=409, detail="Seat availability changed, please try again")

        # Create the booking with PENDING status
        db_booking = models.Booking(
            user_id=current_user.id,
            flight_id=booking.flight_id,
            seats=booking.seats,
            status="PENDING"
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)

        # Simulate payment
        payment_result = mock_payment_service(db_booking.id, force_failure=force_payment_failure)

        if payment_result["status"] == "SUCCESS":
            db_booking.status = "CONFIRMED"
            db_booking.payment_ref = payment_result["payment_ref"]
            
            # On success, publish the flight ID to the seat_updates channel
            redis_client.publish("seat_updates", str(booking.flight_id))
            
        else:
            # Payment failed, perform compensating action
            db_booking.status = "FAILED"
            
            # Atomically return the reserved seats to Redis
            with redis_client.pipeline() as pipe:
                pipe.incrby(seat_key, booking.seats)
                pipe.hincrby(flight_key, "available_seats", booking.seats)
                pipe.execute()
            
            # NOTE: We do NOT update the master DB record here, because the seats were never taken from it.

        db.commit()
        db.refresh(db_booking)
        
        return db_booking

@router.get("/bookings", response_model=list[schemas.Booking])
def get_my_bookings(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()

@router.delete("/bookings/{booking_id}", response_model=schemas.Booking)
def cancel_booking(booking_id: UUID, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis), current_user: models.User = Depends(get_current_user)):
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()

    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if db_booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this booking")

    if db_booking.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Booking is already cancelled")

    if db_booking.status == "FAILED":
        raise HTTPException(status_code=400, detail="Cannot cancel a failed booking")

    if db_booking.status == "PENDING":
        raise HTTPException(status_code=400, detail="Cannot cancel a pending booking")

    # Update booking status in DB
    db_booking.status = "CANCELLED"
    
    # Atomically increment seat count in Redis
    flight_key = f"flight:{db_booking.flight_id}"
    seat_key = f"flight_seats:{db_booking.flight_id}"
    
    with redis_client.pipeline() as pipe:
        pipe.incrby(seat_key, db_booking.seats)
        pipe.hincrby(flight_key, "available_seats", db_booking.seats)
        pipe.execute()

    # Update available_seats in the master DB record
    db.query(models.Flight).filter(models.Flight.id == db_booking.flight_id).update(
        {"available_seats": models.Flight.available_seats + db_booking.seats},
        synchronize_session=False
    )
    
    db.commit()
    db.refresh(db_booking)
    
    return db_booking
