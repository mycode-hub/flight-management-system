from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas import schemas
from app.models import models
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.services import redis_service
from uuid import UUID, uuid4
import redis
import csv
import io
import json
from datetime import datetime

router = APIRouter()

def process_bulk_upload(file_contents: bytes, db: Session, redis_client: redis.Redis, job_id: str):
    """
    Background task to process the uploaded CSV file.
    Performs an "upsert" logic for each row.
    """
    results = {
        "status": "IN_PROGRESS",
        "created": 0,
        "updated": 0,
        "failed": 0,
        "errors": []
    }
    redis_client.set(f"bulk_job:{job_id}", json.dumps(results))

    try:
        # Use io.StringIO to treat the byte string as a file
        csv_reader = csv.DictReader(io.StringIO(file_contents.decode('utf-8')))
        
        for row in csv_reader:
            try:
                flight_data = schemas.FlightCreate(**row)
                
                # Upsert logic: Check if flight exists
                db_flight = db.query(models.Flight).filter(
                    models.Flight.flight_number == flight_data.flight_number,
                    models.Flight.departure_ts == flight_data.departure_ts
                ).first()

                if db_flight:
                    # Update existing flight
                    redis_service.delete_flight_from_redis(redis_client, db_flight)
                    for var, value in vars(flight_data).items():
                        setattr(db_flight, var, value) if value else None
                    db_flight.available_seats = flight_data.total_seats
                    results["updated"] += 1
                else:
                    # Create new flight
                    db_flight = models.Flight(**flight_data.dict(), available_seats=flight_data.total_seats)
                    db.add(db_flight)
                    results["created"] += 1
                
                db.commit()
                db.refresh(db_flight)
                redis_service.update_flight_in_redis(redis_client, db_flight)

            except Exception as e:
                db.rollback()
                results["failed"] += 1
                results["errors"].append(f"Row {csv_reader.line_num}: {str(e)}")

        results["status"] = "COMPLETED"
    except Exception as e:
        results["status"] = "FAILED"
        results["errors"].append(f"Critical error: {str(e)}")
    
    redis_client.set(f"bulk_job:{job_id}", json.dumps(results), ex=3600) # Keep result for 1 hour


@router.post("/flights/bulk-upload")
def bulk_upload_flights(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    if file.content_type != 'text/csv':
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    job_id = str(uuid4())
    file_contents = file.file.read()

    # Start the background task
    background_tasks.add_task(process_bulk_upload, file_contents, db, redis_client, job_id)
    
    return {"job_id": job_id, "status": "PENDING", "message": "File upload successful. Processing in the background."}

@router.get("/flights/bulk-upload/status/{job_id}")
def get_bulk_upload_status(job_id: str, redis_client: redis.Redis = Depends(get_redis)):
    result = redis_client.get(f"bulk_job:{job_id}")
    if not result:
        raise HTTPException(status_code=404, detail="Job not found.")
    return json.loads(result)

@router.post("/flights", response_model=schemas.Flight)
def create_flight(flight: schemas.FlightCreate, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    db_flight = models.Flight(**flight.dict(), available_seats=flight.total_seats)
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    
    # Update Redis cache
    redis_service.update_flight_in_redis(redis_client, db_flight)
    
    return db_flight

@router.get("/flights/{flight_id}", response_model=schemas.Flight)
def read_flight(flight_id: UUID, db: Session = Depends(get_db)):
    db_flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if db_flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    return db_flight

@router.put("/flights/{flight_id}", response_model=schemas.Flight)
def update_flight(flight_id: UUID, flight: schemas.FlightCreate, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    db_flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if db_flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    # First, remove old data from Redis
    redis_service.delete_flight_from_redis(redis_client, db_flight)

    # Update DB
    for var, value in vars(flight).items():
        setattr(db_flight, var, value) if value else None

    db_flight.available_seats = flight.total_seats
    db.commit()
    db.refresh(db_flight)

    # Add new data to Redis
    redis_service.update_flight_in_redis(redis_client, db_flight)

    return db_flight

@router.delete("/flights/{flight_id}", response_model=schemas.Flight)
def delete_flight(flight_id: UUID, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)):
    db_flight = db.query(models.Flight).filter(models.Flight.id == flight_id).first()
    if db_flight is None:
        raise HTTPException(status_code=404, detail="Flight not found")
    
    # Delete from Redis first
    redis_service.delete_flight_from_redis(redis_client, db_flight)

    # Delete from DB
    db.delete(db_flight)
    db.commit()
    return db_flight
