import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { createBooking } from '../services/api';
import { Booking } from '../types';

const BookingPage: React.FC = () => {
  const { flightId } = useParams<{ flightId: string }>();
  const [seats, setSeats] = useState(1);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBooking = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flightId) {
      setError('Flight ID is missing.');
      return;
    }
    try {
      const newBooking = await createBooking({ flight_id: flightId, seats });
      setBooking(newBooking);
      setError(null);
    } catch (err) {
      setError('Error creating booking. Please try again.');
      setBooking(null);
    }
  };

  return (
    <div className="container">
      <h1 className="my-4">Book Flight</h1>
      {booking ? (
        <div className="alert alert-success">
          Booking successful! Your booking ID is {booking.id}.
        </div>
      ) : (
        <form onSubmit={handleBooking}>
          <div className="form-group">
            <label>Seats</label>
            <input
              type="number"
              className="form-control"
              value={seats}
              onChange={(e) => setSeats(parseInt(e.target.value))}
              min="1"
              required
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Confirm Booking
          </button>
          {error && <div className="alert alert-danger mt-3">{error}</div>}
        </form>
      )}
    </div>
  );
};

export default BookingPage;
