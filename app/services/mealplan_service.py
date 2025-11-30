import json
import os
from typing import List
from app.models.meal_schema import (
    MealPlanRequest, 
    TDietPlan,
    TMealWithTime,
    TMeal,
    TMacroNutrients,
    TMicroNutrients,
    TNutrient
)
from openai import OpenAI
from pydantic import BaseModel
from app.config.settings import OPENAI_API_KEY

from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Structured Output Models for OpenAI
# -----------------------------
class MealPlanOutput(BaseModel):
    """Output schema for OpenAI structured output"""
    dailyMeals: List[TMealWithTime]

# -----------------------------
# TDEE & Macro Calculation
# -----------------------------
def calculate_bmr(user_profile: dict) -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
    """
    weight = user_profile["weight_kg"]
    height = user_profile["height_cm"]
    age = user_profile["age"]
    gender = user_profile["gender"].lower()
    
    if gender == "male":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:  # female
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    return bmr

def get_activity_multiplier(activity_level: str) -> float:
    """
    Get activity multiplier based on activity level.
    """
    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    return multipliers.get(activity_level.lower(), 1.55)

def calculate_tdee_and_macros(request: MealPlanRequest) -> dict:
    """
    Calculate TDEE and macro distribution based on user profile and goals.
    Returns dict with calorie_target, protein_g, carbs_g, fats_g.
    """
    user_profile = {
        "weight_kg": request.user_profile.weight_kg,
        "height_cm": request.user_profile.height_cm,
        "age": request.user_profile.age,
        "gender": request.user_profile.gender
    }
    
    # Calculate BMR
    bmr = calculate_bmr(user_profile)
    
    # Calculate TDEE (Total Daily Energy Expenditure)
    activity_multiplier = get_activity_multiplier(request.user_profile.activity_level)
    tdee = bmr * activity_multiplier
    
    # Adjust for goal (using new field name: fitness_goal)
    goal = request.fitness_goal.lower()
    if goal == "cutting":
        calorie_target = int(tdee - 500)  # 500 cal deficit
    elif goal == "bulking":
        calorie_target = int(tdee + 300)  # 300 cal surplus
    else:  # maintenance
        calorie_target = int(tdee)
    
    # Calculate macros with balanced approach (customization removed)
    # Default balanced macro split
    protein_ratio = 0.25  # 25% protein
    carbs_ratio = 0.50    # 50% carbs
    fats_ratio = 0.25     # 25% fats
    
    # Calculate macro grams (protein: 4 cal/g, carbs: 4 cal/g, fats: 9 cal/g)
    protein_g = int((calorie_target * protein_ratio) / 4)
    carbs_g = int((calorie_target * carbs_ratio) / 4)
    fats_g = int((calorie_target * fats_ratio) / 9)
    
    return {
        "calorie_target": calorie_target,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fats_g": fats_g,
        "tdee_estimation_method": "mifflin-st-jeor + activity multiplier + goal adjustment"
    }



# -----------------------------
# Meal Plan Generation
# -----------------------------
async def generate_meal_plan(request: MealPlanRequest) -> TDietPlan:
    """
    Generate meal plan using OpenAI Structured Outputs for optimal performance.
    """
    # Calculate TDEE and macros
    nutrition_data = calculate_tdee_and_macros(request)
    
    # Build dietary requirements string
    diet_type = request.dietary_preferences.diet_type
    restrictions = request.dietary_preferences.restrictions
    restrictions_str = ", ".join(restrictions) if restrictions else "None"
    location = request.user_profile.location
    
    # Simplified, concise prompt for faster processing
    user_prompt = f"""Create a {request.number_of_days}-day meal plan.

User: {request.user_profile.age}yo {request.user_profile.gender}, {request.user_profile.weight_kg}kg, {request.user_profile.height_cm}cm, {request.user_profile.activity_level}
Location: {location}
Goal: {request.fitness_goal}

Daily Targets: {nutrition_data['calorie_target']} cal, {nutrition_data['protein_g']}g protein, {nutrition_data['carbs_g']}g carbs, {nutrition_data['fats_g']}g fats

Diet: {diet_type}, Restrictions: {restrictions_str}

Create {request.number_of_days * 4} meals ({request.number_of_days} days × 4 meals/day: breakfast, lunch, snack, dinner).
Use local {location} ingredients. Keep meals practical and culturally appropriate.
Include only the top 3-4 most significant vitamins and minerals per meal."""

    try:
        # Use structured outputs for guaranteed format and faster performance
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert nutritionist creating structured meal plans. Output only valid structured data."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format=MealPlanOutput,
            temperature=0,  # Deterministic, faster
        )
        
        # Extract the parsed response
        meal_plan_output = completion.choices[0].message.parsed
        
        if not meal_plan_output or not meal_plan_output.dailyMeals:
            raise ValueError("Failed to generate meal plan - empty response")
        
        # Return TDietPlan directly
        return TDietPlan(
            user_id=None,
            dailyMeals=meal_plan_output.dailyMeals
        )
        
    except Exception as e:
        # Fallback error handling
        raise ValueError(f"Failed to generate meal plan: {str(e)}")



# -----------------------------
# Meal Plan Update/Refinement
# -----------------------------
async def update_meal_plan(original_diet_plan: dict, feedback: str, user_id: str = None) -> TDietPlan:
    """
    Update/refine an existing meal plan based on user feedback using OpenAI Structured Outputs.
    
    Args:
        original_diet_plan: Dictionary containing dailyMeals array
        feedback: User's feedback on the meal plan
        user_id: Optional user identifier
    
    Returns:
        TDietPlan: Updated meal plan
    """
    # Convert original plan to JSON string for the prompt
    original_plan_json = json.dumps(original_diet_plan, indent=2)
    
    # Simplified prompt
    user_prompt = f"""Refine this meal plan based on user feedback.

Original Plan:
{original_plan_json}

User Feedback: "{feedback}"

Instructions:
- If feedback requests changes: modify the plan accordingly (swap foods, adjust portions, change diet type, etc.)
- If feedback is just positive (e.g., "great!", "love it"): keep plan unchanged
- Maintain same meal structure and nutritional balance
- Include only top 3-4 vitamins/minerals per meal"""

    try:
        # Use structured outputs for guaranteed format and faster performance
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert nutritionist updating meal plans based on user feedback. Output only valid structured data."
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            response_format=MealPlanOutput,
            temperature=0,  # Deterministic, faster
        )
        
        # Extract the parsed response
        meal_plan_output = completion.choices[0].message.parsed
        
        if not meal_plan_output or not meal_plan_output.dailyMeals:
            raise ValueError("Failed to update meal plan - empty response")
        
        # Return updated TDietPlan
        return TDietPlan(
            user_id=user_id,
            dailyMeals=meal_plan_output.dailyMeals
        )
        
    except Exception as e:
        # Fallback error handling
        raise ValueError(f"Failed to update meal plan: {str(e)}")
