from typing import List, Optional
from pydantic import BaseModel, Field


class FoodNutritionRequest(BaseModel):
    """Request body for food-name-based nutrition lookup."""
    food_name: str = Field(..., description="Name of the food item to analyze")


class FoodMicroNutrient(BaseModel):
    """Micronutrient with amount that must include a unit."""
    name: str = Field(..., description="Micronutrient name (e.g., Iron, Vitamin C)")
    amount: str = Field(
        ...,
        description="Amount with unit (e.g., '4.6mg', '2.2mcg', '0.3g', '120IU')",
        pattern=r"^\s*\d+(\.\d+)?\s*(mg|mcg|g|iu|IU)\s*$",
    )


class FoodNutritionResponse(BaseModel):
    """Response body for food-name-based nutrition lookup (100g basis)."""
    total_protein_g: str = Field(..., description="Total protein in grams")
    total_carbs_g: str = Field(..., description="Total carbohydrates in grams")
    total_fats_g: str = Field(..., description="Total fats in grams")
    total_fiber_g: str = Field(..., description="Total fiber in grams")
    micro_nutrients: Optional[List[FoodMicroNutrient]] = Field(
        default=None,
        description="Micronutrients with explicit unit in amount field",
    )
    total_calories: str = Field(..., description="Total calories")
