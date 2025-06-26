from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.models.workout_schema import ExerciseRequest, CalorieResponse
from app.services.workout_calorie_burn_calculation import calculate_calories_with_openai

router = APIRouter(prefix="/workout-calorie", tags=["Workout Calorie Calculation"])

@router.post("/calculate-calories", response_model=CalorieResponse)
async def calculate_calories(exercise_data: ExerciseRequest):
    try:
        # NOTE: Ensure the 'openai' package is installed in your environment: pip install openai
        import openai
        if not openai.api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.")
        # Map ExerciseRequest fields to the expected dict keys for the AI function
        exercise_dict = {
            "userHight": exercise_data.height,  # Note: API expects 'userHight' (cm), model uses 'height' (feet)
            "userWeight": exercise_data.body_weight,
            "exerciseName": exercise_data.exerciseName,
            "exerciseType": exercise_data.exerciseType,
            "exerciseDescription": getattr(exercise_data, "exerciseDescription", ""),
            "weightLifted": exercise_data.weightLifted,
            "reps": exercise_data.reps,
            "set": getattr(exercise_data, "sets", None) or exercise_data.sets,
            "resetTime": getattr(exercise_data, "resetTime", None) or exercise_data.resetTime,
            "restime": getattr(exercise_data, "restTime", None) or exercise_data.restTime
        }
        calculation_result = calculate_calories_with_openai(exercise_dict)
        response = CalorieResponse(
            total_calories_burned=calculation_result["total_calories_burned"],
            # calories_per_set=calculation_result["calories_per_set"],
            # total_exercise_time=calculation_result["total_exercise_time_seconds"],
            exercise_details={
                "exercise_name": exercise_data.exerciseName,
                "exercise_type": exercise_data.exerciseType,
                "exercise_description": exercise_data.exerciseDescription,
                "weight_lifted": exercise_data.weightLifted,
                "reps": exercise_data.reps,
                "sets": exercise_data.sets,
                "resetTime": exercise_data.resetTime,
                "rest_time": exercise_data.restTime,
                "body_weight": exercise_data.body_weight,
                "height": exercise_data.height
            },
            # calculation_method=calculation_result["calculation_method"],
            # timestamp=datetime.now()
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating calories: {str(e)}")

@router.get("/")
async def root():
    return {
        "message": "Calorie Calculator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /workout-calorie/calculate-calories": "Calculate calories burned for an exercise session"
        }
    }

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}
