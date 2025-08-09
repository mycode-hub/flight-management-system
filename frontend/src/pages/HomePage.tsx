import React, { useState } from 'react';
import { searchFlights } from '../services/api';
import { Flight } from '../types';
import FlightResults from '../components/FlightResults';
import SearchForm from '../components/SearchForm';

const HomePage: React.FC = () => {
  const [flights, setFlights] = useState<Flight[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (source: string, destination: string, date: string) => {
    try {
      const results = await searchFlights(source, destination, date);
      setFlights(results);
      setError(null);
    } catch (err) {
      setError('Error searching for flights. Please try again.');
      setFlights([]);
    }
  };

  return (
    <div className="container">
      <h1 className="my-4">Flight Search</h1>
      <SearchForm onSearch={handleSearch} />
      {error && <div className="alert alert-danger">{error}</div>}
      <FlightResults flights={flights} />
    </div>
  );
};

export default HomePage;
