from fastapi import FastAPI
from app.api.v1 import admin, search, booking
from app.core.database import engine
from app.models import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Flight Management System")

app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(booking.router, prefix="/api/v1", tags=["booking"])

@app.get("/")
def root():
    return {"message": "Flight Management Backend Running"}
