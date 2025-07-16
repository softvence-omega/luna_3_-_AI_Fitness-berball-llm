# app/api/separate.py
from fastapi import APIRouter
from app.services.separate import example_service_function

router = APIRouter()

@router.get("/example-endpoint")
def example_endpoint(data: str):
    """
    Example endpoint that uses a service function.
    """
    return {"result": example_service_function(data)}

# Add more endpoints here as needed 