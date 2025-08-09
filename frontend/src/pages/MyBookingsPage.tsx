import React, { useState, useEffect } from 'react';
import { getMyBookings, cancelBooking } from '../services/api';
import { Booking } from '../types';

const MyBookingsPage: React.FC = () => {
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchBookings = async () => {
    try {
      const myBookings = await getMyBookings();
      setBookings(myBookings);
    } catch (err) {
      setError('Error fetching bookings.');
    }
  };

  useEffect(() => {
    fetchBookings();
  }, []);

  const handleCancelBooking = async (bookingId: string) => {
    try {
      await cancelBooking(bookingId);
      fetchBookings(); // Refresh the list of bookings
    } catch (err) {
      setError('Error cancelling booking.');
    }
  };

  return (
    <div className="container">
      <h1 className="my-4">My Bookings</h1>
      {error && <div className="alert alert-danger">{error}</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Booking ID</th>
            <th>Flight ID</th>
            <th>Seats</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {bookings.map((booking) => (
            <tr key={booking.id}>
              <td>{booking.id}</td>
              <td>{booking.flight_id}</td>
              <td>{booking.seats}</td>
              <td>{booking.status}</td>
              <td>
                {booking.status === 'CONFIRMED' && (
                  <button
                    className="btn btn-danger"
                    onClick={() => handleCancelBooking(booking.id)}
                  >
                    Cancel
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default MyBookingsPage;
