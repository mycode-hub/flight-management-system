import axios from 'axios';
import { Flight, Booking, BookingCreate } from '../types';

const API_URL = 'http://localhost:8000';

export const searchFlights = async (source: string, destination: string, date: string): Promise<Flight[]> => {
  const response = await axios.get(`${API_URL}/api/v1/search`, {
    params: { source, destination, date },
  });
  return response.data;
};

export const createBooking = async (booking: BookingCreate): Promise<Booking> => {
  const response = await axios.post(`${API_URL}/api/v1/booking`, booking);
  return response.data;
};

export const createFlight = async (flight: Omit<Flight, 'id' | 'available_seats'>): Promise<Flight> => {
  const response = await axios.post(`${API_URL}/admin/flights`, flight);
  return response.data;
};

export const getAirports = async (): Promise<string[]> => {
  const response = await axios.get(`${API_URL}/api/v1/airports`);
  return response.data;
};

export const bulkUploadFlights = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_URL}/admin/flights/bulk-upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getBulkUploadStatus = async (jobId: string): Promise<any> => {
  const response = await axios.get(`${API_URL}/admin/flights/bulk-upload/status/${jobId}`);
  return response.data;
};


