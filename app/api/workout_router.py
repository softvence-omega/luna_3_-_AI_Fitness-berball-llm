# api/workout_router.py
# This file defines the API endpoints for creating and updating workout plans.

from fastapi import APIRouter, HTTPException
from models.workout_schema import WorkoutPlanRequest, WorkoutPlanResponse, WorkoutUpdateRequest
from services import workout_service

router = APIRouter(
    tags=["Workout"],
)

@router.post("/create-workout-plan", response_model=WorkoutPlanResponse)
async def create_workout_plan(request: WorkoutPlanRequest):
    """
    Creates a personalized workout plan based on user details.
    
    This endpoint takes user information (age, goals, fitness level, etc.)
    and uses the workout service to generate a structured workout plan.
    """
    try:
        workout_plan = await workout_service.generate_workout_plan(request)
        return workout_plan
    except Exception as e:
        # In a production environment, you would log the error `e`
        raise HTTPException(status_code=500, detail=f"Failed to create workout plan: {e}")

@router.post("/update-workout-plan", response_model=WorkoutPlanResponse)
async def update_workout_plan(request: WorkoutUpdateRequest):
    """
    Updates an existing workout plan based on user feedback.
    
    This endpoint takes the original workout plan and user feedback,
    then uses the workout service to generate a revised plan.
    """
    try:
        updated_plan = await workout_service.refine_workout_plan(request)
        return updated_plan
    except Exception as e:
        # In a production environment, you would log the error `e`
        raise HTTPException(status_code=500, detail=f"Failed to update workout plan: {e}")
