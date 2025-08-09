import React, { useState, useEffect } from 'react';
import { createFlight, bulkUploadFlights, getBulkUploadStatus } from '../services/api';
import { Flight } from '../types';

const AdminPage: React.FC = () => {
  const [flightNumber, setFlightNumber] = useState('');
  const [source, setSource] = useState('');
  const [destination, setDestination] = useState('');
  const [departureTs, setDepartureTs] = useState('');
  const [arrivalTs, setArrivalTs] = useState('');
  const [totalSeats, setTotalSeats] = useState(100);
  const [price, setPrice] = useState(500);
  const [newFlight, setNewFlight] = useState<Flight | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<any | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      const interval = setInterval(async () => {
        try {
          const status = await getBulkUploadStatus(jobId);
          setUploadStatus(status);
          if (status.status === 'COMPLETED' || status.status === 'FAILED') {
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Error fetching upload status:', err);
          clearInterval(interval);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [jobId]);

  const handleAddFlight = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const flightData = {
        flight_number: flightNumber,
        source,
        destination,
        departure_ts: departureTs,
        arrival_ts: arrivalTs,
        total_seats: totalSeats,
        price,
      };
      const result = await createFlight(flightData);
      setNewFlight(result);
      setError(null);
    } catch (err) {
      setError('Error creating flight. Please try again.');
      setNewFlight(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setUploadFile(e.target.files[0]);
    }
  };

  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setError('Please select a file to upload.');
      return;
    }

    try {
      const result = await bulkUploadFlights(uploadFile);
      setJobId(result.job_id);
      setError(null);
    } catch (err) {
      setError('Error uploading file. Please try again.');
      setJobId(null);
    }
  };

  return (
    <div className="container">
      <div className="row">
        <div className="col-md-6">
          <h1 className="my-4">Admin - Add Flight</h1>
          {newFlight ? (
            <div className="alert alert-success">
              Flight created successfully! Flight ID is {newFlight.id}.
            </div>
          ) : (
            <form onSubmit={handleAddFlight}>
              <div className="form-group">
                <label>Flight Number</label>
                <input
                  type="text"
                  className="form-control"
                  value={flightNumber}
                  onChange={(e) => setFlightNumber(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Source</label>
                <input
                  type="text"
                  className="form-control"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Destination</label>
                <input
                  type="text"
                  className="form-control"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Departure Time</label>
                <input
                  type="datetime-local"
                  className="form-control"
                  value={departureTs}
                  onChange={(e) => setDepartureTs(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Arrival Time</label>
                <input
                  type="datetime-local"
                  className="form-control"
                  value={arrivalTs}
                  onChange={(e) => setArrivalTs(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Total Seats</label>
                <input
                  type="number"
                  className="form-control"
                  value={totalSeats}
                  onChange={(e) => setTotalSeats(parseInt(e.target.value))}
                  required
                />
              </div>
              <div className="form-group">
                <label>Price</label>
                <input
                  type="number"
                  className="form-control"
                  value={price}
                  onChange={(e) => setPrice(parseFloat(e.target.value))}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">
                Add Flight
              </button>
              {error && <div className="alert alert-danger mt-3">{error}</div>}
            </form>
          )}
        </div>
        <div className="col-md-6">
          <h1 className="my-4">Admin - Bulk Upload</h1>
          <form onSubmit={handleBulkUpload}>
            <div className="form-group">
              <label>Upload CSV File</label>
              <input
                type="file"
                className="form-control-file"
                onChange={handleFileChange}
                accept=".csv"
              />
            </div>
            <button type="submit" className="btn btn-primary">
              Upload
            </button>
            {error && <div className="alert alert-danger mt-3">{error}</div>}
          </form>
          {uploadStatus && (
            <div className="mt-4">
              <h3>Upload Status</h3>
              <p>Status: {uploadStatus.status}</p>
              <p>Created: {uploadStatus.created}</p>
              <p>Updated: {uploadStatus.updated}</p>
              <p>Failed: {uploadStatus.failed}</p>
              {uploadStatus.errors && uploadStatus.errors.length > 0 && (
                <div>
                  <h4>Errors:</h4>
                  <ul>
                    {uploadStatus.errors.map((err: string, index: number) => (
                      <li key={index}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
