from fastapi import APIRouter, HTTPException
from app.models.meal_schema import MealPlanRequest, TDietPlan, MealPlanUpdateRequest
from app.services.mealplan_service import generate_meal_plan, update_meal_plan

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

@router.post("/update", response_model=TDietPlan)
async def mealplan_update(request: MealPlanUpdateRequest):
    """
    Update/refine an existing meal plan based on user feedback.
    
    This endpoint takes the current meal plan and user feedback,
    then uses the meal plan service to generate a refined plan.
    """
    try:
        # Convert the request dailyMeals to dict format for the service
        original_plan = {"dailyMeals": [meal.dict() for meal in request.dailyMeals]}
        
        result = await update_meal_plan(
            original_diet_plan=original_plan,
            feedback=request.feedback,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

