import axios from 'axios';
import { Flight, Booking, BookingCreate } from '../types';

const API_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const searchFlights = async (source: string, destination: string, date: string): Promise<Flight[]> => {
  const response = await api.get('/api/v1/search', {
    params: { source, destination, date },
  });
  return response.data;
};

export const createBooking = async (booking: BookingCreate): Promise<Booking> => {
  const response = await api.post('/api/v1/booking', booking);
  return response.data;
};

export const createFlight = async (flight: Omit<Flight, 'id' | 'available_seats'>): Promise<Flight> => {
  const response = await api.post('/admin/flights', flight);
  return response.data;
};

export const getAirports = async (): Promise<string[]> => {
  const response = await api.get('/api/v1/airports');
  return response.data;
};

export const bulkUploadFlights = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/admin/flights/bulk-upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getBulkUploadStatus = async (jobId: string): Promise<any> => {
  const response = await api.get(`/admin/flights/bulk-upload/status/${jobId}`);
  return response.data;
};

export const login = async (username: string, password: string): Promise<string> => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);

  const response = await api.post('/api/v1/auth/token', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  const { access_token } = response.data;
  localStorage.setItem('token', access_token);
  return access_token;
};

export const register = async (username: string, password: string): Promise<any> => {
  try {
    const response = await api.post('/api/v1/auth/register', { username, password });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.status === 400) {
      throw new Error('Username already registered.');
    }
    throw new Error('An unknown error occurred.');
  }
};

export const logout = () => {
  localStorage.removeItem('token');
};

export const getMyBookings = async (): Promise<Booking[]> => {
  const response = await api.get('/api/v1/bookings');
  return response.data;
};

export const cancelBooking = async (bookingId: string): Promise<Booking> => {
  const response = await api.delete(`/api/v1/bookings/${bookingId}`);
  return response.data;
};


