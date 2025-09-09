from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import nutrition_service
from app.models.nutrition_schema import NutritionResponse


router = APIRouter(
    tags=["Nutrition"],
)

@router.post("/analyze-meal-nutrition", response_model=NutritionResponse)
async def analyze_meal_nutrition(image: UploadFile = File(...)):
    """
    Analyzes the nutritional content of a meal from an uploaded image.
    
    This endpoint accepts an image file, passes it to the nutrition analysis
    service, and returns a detailed breakdown of its nutritional content.
    """
    try:
        content = await image.read()
        return await nutrition_service.get_nutritional_analysis(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred during nutrition analysis.")
