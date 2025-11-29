from pydantic import BaseModel
from typing import List, Optional, Literal
from bson import ObjectId

# ==================== Request Models ====================

class DietaryPreferences(BaseModel):
    """Renamed from DietPreferences"""
    diet_type: str  # e.g., "balanced", "keto", "vegan"
    restrictions: List[str] = []  # e.g., ["halal", "gluten-free"]

class UserProfile(BaseModel):
    user_id: Optional[str] = None  # Using string instead of ObjectId for API responses
    age: int
    gender: str  # "male" or "female"
    weight_kg: float
    height_cm: float
    activity_level: str  # "sedentary", "light", "moderate", "active", "very_active"
    location: str  # NEW: e.g., "Dhaka, Bangladesh"

class MealPlanRequest(BaseModel):
    user_profile: UserProfile
    fitness_goal: str  # "maintenance", "cutting", "bulking" (renamed from 'goal')
    dietary_preferences: DietaryPreferences  # renamed from 'diet_preferences'
    duration_type: str  # "daily" or "weekly" (renamed from 'meal_plan_type')
    number_of_days: int


# ==================== Response Models - New TypeScript-aligned Schema ====================

class TNutrient(BaseModel):
    """Individual nutrient with name, quantity, and unit"""
    name: str
    quantity: float
    unit: str  # mg, mcg, g, IU, etc.

class TMicroNutrients(BaseModel):
    """Micronutrients container for vitamins and minerals"""
    vitamins: List[TNutrient]
    minerals: List[TNutrient]

class TMacroNutrients(BaseModel):
    """Macronutrients - calories, protein, carbs, fats"""
    calories: int
    protein: int
    carbs: int
    fats: int

class TMeal(BaseModel):
    """Meal details with food items and nutrition info"""
    foodName: List[str]  # Array of food items (e.g., ["Chicken Breast", "Brown Rice"])
    dailyServingSize: str  # e.g., "150g chicken, 200g rice"
    macroNutrients: Optional[TMacroNutrients] = None
    microNutrients: Optional[TMicroNutrients] = None

class TMealWithTime(BaseModel):
    """Meal with time slot"""
    mealTime: Literal["breakfast", "lunch", "dinner", "snack"]
    mealDetails: TMeal

class TDietPlan(BaseModel):
    """Complete diet plan structure"""
    user_id: Optional[str] = None  # Using string instead of ObjectId for API responses
    dailyMeals: List[TMealWithTime]


# ==================== Summary and Response Wrapper ====================

class MacroSplit(BaseModel):
    protein_g: int
    carbs_g: int
    fats_g: int

class MealPlanSummary(BaseModel):
    goal: str
    calorie_target: int
    macro_split: MacroSplit
    tdee_estimation_method: str

class AdjustmentOptions(BaseModel):
    can_regenerate: bool = True
    suggestions: List[str] = ["reduce_carbs", "increase_protein", "swap_meal", "remove_ingredient"]

class MealPlanResponse(BaseModel):
    """API Response wrapper"""
    status: str
    summary: MealPlanSummary
    diet_plan: TDietPlan  # Main diet plan with new structure
    adjustment_options: AdjustmentOptions

class MealPlanUpdateRequest(BaseModel):
    """Request model for updating/refining an existing meal plan"""
    user_id: Optional[str] = None
    dailyMeals: List[TMealWithTime]
    feedback: str
