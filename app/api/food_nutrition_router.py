from fastapi import APIRouter, HTTPException
from app.models.food_nutrition_schema import FoodNutritionRequest, FoodNutritionResponse
from app.services import food_nutrition_service


router = APIRouter(
    tags=["Nutrition"],
)


@router.post("/analyze-food-nutrition-100g", response_model=FoodNutritionResponse)
async def analyze_food_nutrition_100g(request: FoodNutritionRequest):
    """Return nutrition estimation per 100g for the given food name."""
    try:
        return await food_nutrition_service.get_food_nutrition_per_100g(request.food_name)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An error occurred during food nutrition analysis.",
        )
