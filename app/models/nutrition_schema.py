from pydantic import BaseModel

class NutritionResponse(BaseModel):
    """
    Schema for the response body of the /analyze-meal-nutrition endpoint.
    """
    total_protein_g: str
    total_carbs_g: str
    total_fats_g: str
    total_fiber_g: str
    total_calories: str
