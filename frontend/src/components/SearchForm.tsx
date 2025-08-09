import React, { useState, useEffect } from 'react';
import { getAirports } from '../services/api';

interface SearchFormProps {
  onSearch: (source: string, destination: string, date: string) => void;
}

const SearchForm: React.FC<SearchFormProps> = ({ onSearch }) => {
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [airports, setAirports] = useState<string[]>([]);
  const [sourceSuggestions, setSourceSuggestions] = useState<string[]>([]);
  const [destinationSuggestions, setDestinationSuggestions] = useState<string[]>([]);

  useEffect(() => {
    const fetchAirports = async () => {
      try {
        const airportList = await getAirports();
        setAirports(airportList);
      } catch (error) {
        console.error('Error fetching airports:', error);
      }
    };
    fetchAirports();
  }, []);

  const handleSourceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSource(value);
    if (value) {
      const filtered = airports.filter((airport) =>
        airport.toLowerCase().includes(value.toLowerCase())
      );
      setSourceSuggestions(filtered);
    } else {
      setSourceSuggestions([]);
    }
  };

  const handleDestinationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setDestination(value);
    if (value) {
      const filtered = airports.filter((airport) =>
        airport.toLowerCase().includes(value.toLowerCase())
      );
      setDestinationSuggestions(filtered);
    } else {
      setDestinationSuggestions([]);
    }
  };

  const handleSuggestionClick = (
    suggestion: string,
    setter: React.Dispatch<React.SetStateAction<string>>,
    suggestionSetter: React.Dispatch<React.SetStateAction<string[]>>
  ) => {
    setter(suggestion);
    suggestionSetter([]);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(source, destination, date);
  };

  return (
    <form onSubmit={handleSubmit} className="mb-4">
      <div className="row">
        <div className="col">
          <input
            type="text"
            className="form-control"
            placeholder="Source"
            value={source}
            onChange={handleSourceChange}
            required
          />
          {sourceSuggestions.length > 0 && (
            <ul className="list-group">
              {sourceSuggestions.map((suggestion) => (
                <li
                  key={suggestion}
                  className="list-group-item list-group-item-action"
                  onClick={() => handleSuggestionClick(suggestion, setSource, setSourceSuggestions)}
                >
                  {suggestion}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="col">
          <input
            type="text"
            className="form-control"
            placeholder="Destination"
            value={destination}
            onChange={handleDestinationChange}
            required
          />
          {destinationSuggestions.length > 0 && (
            <ul className="list-group">
              {destinationSuggestions.map((suggestion) => (
                <li
                  key={suggestion}
                  className="list-group-item list-group-item-action"
                  onClick={() =>
                    handleSuggestionClick(suggestion, setDestination, setDestinationSuggestions)
                  }
                >
                  {suggestion}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="col">
          <input
            type="date"
            className="form-control"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>
        <div className="col">
          <button type="submit" className="btn btn-primary">
            Search
          </button>
        </div>
      </div>
    </form>
  );
};

export default SearchForm;
