from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import admin, search, booking, airports, auth
from app.core.database import engine
from app.models import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flight Management System")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(booking.router, prefix="/api/v1", tags=["booking"])
app.include_router(airports.router, prefix="/api/v1", tags=["airports"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Flight Management Backend Running"}
