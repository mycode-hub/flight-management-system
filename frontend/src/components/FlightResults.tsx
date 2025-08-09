import React from 'react';
import { Flight } from '../types';
import { Link } from 'react-router-dom';

interface FlightResultsProps {
  flights: Flight[];
}

const FlightResults: React.FC<FlightResultsProps> = ({ flights }) => {
  if (flights.length === 0) {
    return <p>No flights found.</p>;
  }

  return (
    <div>
      <h2>Flight Results</h2>
      <ul className="list-group">
        {flights.map((flight) => (
          <li key={flight.id} className="list-group-item">
            <div className="d-flex w-100 justify-content-between">
              <h5 className="mb-1">{flight.flight_number}</h5>
              <small>{new Date(flight.departure_ts).toLocaleDateString()}</small>
            </div>
            <p className="mb-1">
              {flight.source} to {flight.destination}
            </p>
            <p className="mb-1">
              Departure: {new Date(flight.departure_ts).toLocaleTimeString()} | Arrival: {new Date(flight.arrival_ts).toLocaleTimeString()}
            </p>
            <p className="mb-1">Price: ${flight.price}</p>
            <p className="mb-1">Available Seats: {flight.available_seats}</p>
            <Link to={`/book/${flight.id}`} className="btn btn-success">
              Book Now
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FlightResults;
