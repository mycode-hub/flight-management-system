import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter()

@router.get("/airports", response_model=List[str])
def get_airports():
    """
    Returns a list of unique airport locations from the flights data.
    """
    try:
        # In a real application, this would be a more robust data source
        df = pd.read_csv("flights.csv")
        
        # Get unique source and destination airports
        source_airports = df["source"].unique()
        destination_airports = df["destination"].unique()
        
        # Combine, sort, and unique the list
        all_airports = sorted(list(set(source_airports) | set(destination_airports)))
        
        return all_airports
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Airports data not found.")
    except Exception as e:
        # Log the error for debugging
        print(f"Error reading or processing airports data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")
