from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

class Exercise(BaseModel):
    """
    Schema for a single exercise within a workout day.
    """
    name: str = Field(..., description="Name of the exercise (e.g., 'Barbell Bench Press', 'Squats').")
    sets: str = Field(..., description="Number of sets to perform (e.g., '3-4').")
    reps: str = Field(..., description="Number of repetitions per set (e.g., '8-12').")
    rest_period_minutes: str = Field(..., description="Rest time in minutes between sets (e.g., '1-2').")

class DailyWorkout(BaseModel):
    """
    Schema for a full day's workout, including a list of exercises.
    """
    day: str = Field(..., description="The day name of the workout week (e.g., Sunday, Wednesday, Friday).")
    focus: str = Field(..., description="The main focus of the day's workout (e.g., 'Chest & Triceps', 'Full Body Strength').")
    exercises: List[Exercise]

class WorkoutPlan(BaseModel):
    """
    The complete workout plan, which includes a list of daily workouts.
    """
    plan: List[DailyWorkout]

class WorkoutPlanRequest(BaseModel):
    """
    Schema for the initial request to create a workout plan.
    """
    age: int = Field(..., example=30)
    gender: Literal['male', 'female', 'other'] = Field(..., example='male')
    weight_kg: float = Field(..., example=85.5)
    height_cm: float = Field(..., example=180.0)
    fitness_level: Literal['beginner', 'intermediate', 'advanced'] = Field(..., example='intermediate')
    main_goal: str = Field(..., description="Primary fitness goal.", example="Build muscle and lose fat")
    days_per_week: int = Field(..., description="How many days a week the user can train.", example=4)
    available_equipment: str = Field(..., description="List of available equipment.", example="Dumbbells, barbells, pull-up bar, resistance bands")
    notes: str | None = Field(None, description="Any additional notes or preferences.", example="I have a previous shoulder injury, so no overhead presses.")

class WorkoutPlanResponse(BaseModel):
    """
    Schema for the response containing the generated workout plan.
    This will be used for both creation and updates.
    """
    workout_plan: WorkoutPlan

class WorkoutUpdateRequest(BaseModel):
    """
    Schema for the request to update an existing workout plan.
    """
    original_plan: WorkoutPlan
    feedback: str = Field(..., description="User's feedback on the plan.", example="The leg day was too intense. Can we reduce the volume a bit? Also, I'd like to add more focus on my biceps.")

class ExerciseRequest(BaseModel):
    body_weight: float = Field(..., description="Body weight in kg", gt=0)
    height: float = Field(..., description="Height in feet", gt=0)
    exerciseName: str = Field(..., description="Name of the exercise")
    exerciseType: str = Field(..., description="Type of exercise (cardio, strength, etc.)")
    exerciseDescription: str = Field(..., description="Description of the exercise")
    resetTime: float = Field(..., description="Time to complete all reps in seconds", gt=0)
    weightLifted: float = Field(default=0, description="Weight lifted in kg")
    reps: int = Field(..., description="Number of repetitions", gt=0)
    # rep_duration: float = Field(..., description="Time to complete all reps in seconds", gt=0)
    sets: int = Field(..., description="Number of sets", gt=0)
    restTime: float = Field(..., description="Rest time between sets in seconds", ge=0)


class CalorieResponse(BaseModel):
    total_calories_burned: float
    # calories_per_set: float
    # total_exercise_time: float
    exercise_details: dict
    # calculation_method: str
    # timestamp: datetime
