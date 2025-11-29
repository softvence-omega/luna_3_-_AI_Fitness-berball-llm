import json
import os
from app.models.meal_schema import (
    MealPlanRequest, 
    TDietPlan,
    TMealWithTime
)
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config.settings import OPENAI_API_KEY

from dotenv import load_dotenv
load_dotenv()

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
# Initialize LLM
# -----------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    api_key=OPENAI_API_KEY,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


# -----------------------------
# Meal Plan Generation
# -----------------------------
async def generate_meal_plan(request: MealPlanRequest) -> TDietPlan:
    """
    Generate meal plan using ChatOpenAI and return TDietPlan directly.
    """
    # Calculate TDEE and macros
    nutrition_data = calculate_tdee_and_macros(request)
    
    # Build dietary requirements string (using new field names)
    diet_type = request.dietary_preferences.diet_type
    restrictions = request.dietary_preferences.restrictions
    restrictions_str = ", ".join(restrictions) if restrictions else "None"
    location = request.user_profile.location
    
    # Build structured prompt
    user_prompt = f"""
You are a professional nutritionist. Create a {request.number_of_days}-day meal plan with the following requirements:

**User Profile:**
- Age: {request.user_profile.age}, Gender: {request.user_profile.gender}
- Weight: {request.user_profile.weight_kg}kg, Height: {request.user_profile.height_cm}cm
- Activity Level: {request.user_profile.activity_level}
- Location: {location}
- Goal: {request.fitness_goal}

**Nutritional Targets (per day):**
- Calories: {nutrition_data['calorie_target']}
- Protein: {nutrition_data['protein_g']}g
- Carbs: {nutrition_data['carbs_g']}g
- Fats: {nutrition_data['fats_g']}g

**Dietary Requirements:**
- Diet Type: {diet_type}
- Restrictions: {restrictions_str}
- Location Preference: Use locally available ingredients from {location}

**Instructions:**
1. Create {request.number_of_days} day(s) of meals
2. For EACH day, provide 4 meals: breakfast, lunch, snack, and dinner
3. Use ingredients commonly available in {location}
4. Each meal should contribute to hitting the daily calorie and macro targets
5. Respect all dietary restrictions
6. Make meals practical, delicious, and culturally appropriate

**Output Format (STRICT JSON):**
{{
  "dailyMeals": [
    {{
      "mealTime": "breakfast",
      "mealDetails": {{
        "foodName": ["Food 1", "Food 2", "Food 3"],
        "dailyServingSize": "Detailed serving sizes",
        "macroNutrients": {{
          "calories": 500,
          "protein": 30,
          "carbs": 50,
          "fats": 15
        }},
        "microNutrients": {{
          "vitamins": [
            {{"name": "Vitamin C", "quantity": 50, "unit": "mg"}},
            {{"name": "Vitamin D", "quantity": 400, "unit": "IU"}}
          ],
          "minerals": [
            {{"name": "Iron", "quantity": 5, "unit": "mg"}},
            {{"name": "Calcium", "quantity": 200, "unit": "mg"}}
          ]
        }}
      }}
    }},
    {{
      "mealTime": "lunch",
      "mealDetails": {{ ... }}
    }},
    {{
      "mealTime": "snack",
      "mealDetails": {{ ... }}
    }},
    {{
      "mealTime": "dinner",
      "mealDetails": {{ ... }}
    }}
  ]
}}

**CRITICAL:**
- Output ONLY the JSON structure with "dailyMeals" array
- Each day repeats the pattern: breakfast, lunch, snack, dinner
- For {request.number_of_days} days, multiply the meals accordingly
- foodName MUST be an array of strings
- Include realistic micronutrient estimates

Generate the meal plan now in STRICT JSON format.
"""

    messages = [
        SystemMessage(content="You are an expert AI nutritionist creating structured JSON meal plans. Output ONLY valid JSON."),
        HumanMessage(content=user_prompt)
    ]
    
    # Call the LLM
    response = llm.invoke(messages)
    ai_output = response.content
    
    try:
        # Try to parse the JSON response
        parsed_output = json.loads(ai_output)
        daily_meals_data = parsed_output.get("dailyMeals", [])
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract JSON from markdown code blocks
        if "```json" in ai_output:
            start = ai_output.find("```json") + 7
            end = ai_output.find("```", start)
            json_str = ai_output[start:end].strip()
            try:
                parsed_output = json.loads(json_str)
                daily_meals_data = parsed_output.get("dailyMeals", [])
            except json.JSONDecodeError:
                raise ValueError("Failed to parse LLM response as JSON")
        else:
            raise ValueError("Failed to parse LLM response - no JSON found")
    
    # Return TDietPlan directly
    return TDietPlan(
        user_id=None,  # Can be populated from request if needed
        dailyMeals=daily_meals_data
    )
