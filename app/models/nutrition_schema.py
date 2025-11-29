from pydantic import BaseModel, Field
from typing import List, Optional

class MicroNutrient(BaseModel):
    """Individual micronutrient information"""
    name: str = Field(..., description="Name of the micronutrient (e.g., Vitamin C, Iron, Magnesium, Potassium, etc.)")
    amount: str = Field(..., description="Amount with unit (e.g., '50mg', '2mcg')")

class NutritionResponse(BaseModel):
    """
    Schema for the response body of the /analyze-meal-nutrition endpoint.
    """
    total_protein_g: str = Field(..., description="Total protein in grams")
    total_carbs_g: str = Field(..., description="Total carbohydrates in grams")
    total_fats_g: str = Field(..., description="Total fats in grams")
    total_fiber_g: str = Field(..., description="Total fiber in grams")
    micro_nutrients: Optional[List[MicroNutrient]] = Field(default=None, description="List of micronutrients with their amounts")
    total_calories: str = Field(..., description="Total calories")