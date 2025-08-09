import uuid
from sqlalchemy import Column, Integer, String, DateTime, Numeric, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Flight(Base):
    __tablename__ = "flights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number = Column(String, index=True)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_ts = Column(DateTime(timezone=True), nullable=False)
    arrival_ts = Column(DateTime(timezone=True))
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    version = Column(BigInteger, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    bookings = relationship("Booking", back_populates="flight")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    flight_id = Column(UUID(as_uuid=True), ForeignKey("flights.id"))
    seats = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    payment_ref = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.now)
    updated_at = Column(DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    flight = relationship("Flight", back_populates="bookings")
