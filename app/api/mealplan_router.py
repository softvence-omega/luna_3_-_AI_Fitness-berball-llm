from fastapi import APIRouter, HTTPException
from app.models.meal_schema import MealPlanRequest, TDietPlan
from app.services.mealplan_service import generate_meal_plan

router = APIRouter(
    prefix="/mealplan",
    tags=["MealPlan"]
)

import time 

@router.post("/generate", response_model=TDietPlan)
async def mealplan_generate(request: MealPlanRequest):
    try:
        start_time = time.perf_counter()
        result = await generate_meal_plan(request)
        end_time = time.perf_counter()
        print(f"Meal plan generation took {end_time - start_time:.4f} seconds")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
