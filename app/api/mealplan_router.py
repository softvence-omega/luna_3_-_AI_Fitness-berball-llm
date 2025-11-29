from fastapi import APIRouter, HTTPException
from app.models.meal_schema import MealPlanRequest, TDietPlan
from app.services.mealplan_service import generate_meal_plan

router = APIRouter(
    prefix="/mealplan",
    tags=["MealPlan"]
)

@router.post("/generate", response_model=TDietPlan)
async def mealplan_generate(request: MealPlanRequest):
    try:
        result = await generate_meal_plan(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
