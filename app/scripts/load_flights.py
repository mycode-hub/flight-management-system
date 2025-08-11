import csv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Flight
from app.core.config import settings
from datetime import datetime

def load_flights():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    db.query(Flight).delete()
    db.commit()

    with open('flights.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 500:
                break
            flight = Flight(
                flight_number=row['flight_number'],
                source=row['source'],
                destination=row['destination'],
                departure_ts=datetime.fromisoformat(row['departure_ts'].replace('Z', '+00:00')),
                arrival_ts=datetime.fromisoformat(row['arrival_ts'].replace('Z', '+00:00')),
                total_seats=int(row['total_seats']),
                available_seats=int(row['total_seats']),
                price=float(row['price'])
            )
            db.add(flight)
        db.commit()
    db.close()

if __name__ == "__main__":
    load_flights()