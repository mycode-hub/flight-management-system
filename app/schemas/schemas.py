from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class FlightBase(BaseModel):
    flight_number: str
    source: str
    destination: str
    departure_ts: datetime
    arrival_ts: datetime
    total_seats: int
    price: float

class FlightCreate(FlightBase):
    pass

class Flight(FlightBase):
    id: UUID
    available_seats: int
    
    class Config:
        from_attributes = True

class BookingBase(BaseModel):
    user_id: UUID
    flight_id: UUID
    seats: int

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: UUID
    status: str
    payment_ref: str | None = None

    class Config:
        from_attributes = True
