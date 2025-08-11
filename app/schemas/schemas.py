from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List

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

class FlightPath(BaseModel):
    flights: List[Flight]
    total_price: float

class BookingBase(BaseModel):
    flight_id: UUID
    seats: int

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    id: UUID
    user_id: UUID
    status: str
    payment_ref: str | None = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: UUID
    is_admin: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None