export interface Flight {
  id: string;
  flight_number: string;
  source: string;
  destination: string;
  departure_ts: string;
  arrival_ts: string;
  total_seats: number;
  available_seats: number;
  price: number;
}

export interface Booking {
  id: string;
  user_id: string;
  flight_id: string;
  seats: number;
  status: string;
}

export interface BookingCreate {
  flight_id: string;
  seats: number;
  user_id?: string;
}

