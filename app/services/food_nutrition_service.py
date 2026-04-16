import re
from app.config.settings import OPENAI_API_KEY
from app.models.food_nutrition_schema import FoodNutritionResponse
from openai import OpenAI


client = OpenAI(api_key=OPENAI_API_KEY)


def _to_float(value: str) -> float:
    """Parse model numeric strings safely for calorie recalculation."""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


async def get_food_nutrition_per_100g(food_name: str) -> FoodNutritionResponse:
    """
    Estimate nutrition values for a food item per 100 grams.

    Args:
        food_name: Name of the food item.

    Returns:
        FoodNutritionResponse with values normalized to 100g.
    """

    user_prompt = f"""
You are a nutrition expert.

Task:
- Analyze nutrition for exactly 100 grams of this food item: {food_name}
- Return total protein, carbs, fats, fiber, micronutrients, and calories for 100g only.

Rules:
1. Always normalize to 100 grams.
2. If the food is ambiguous, use the most common edible form.
3. If the food is not recognized or is not edible, return zeros and empty micronutrients.
4. Include micronutrients only when meaningful.
5. Do not include explanations.

Output JSON format:
{{
  "total_protein_g": "0",
  "total_carbs_g": "0",
  "total_fats_g": "0",
  "total_fiber_g": "0",
  "micro_nutrients": [
        {{"name": "Iron", "amount": "2.7mg"}}
  ],
  "total_calories": "0"
}}

CRITICAL:
- Keep macro values (protein/carbs/fats/fiber/calories) numeric-only strings.
- For micro_nutrients.amount, unit is mandatory: mg, mcg, g, or IU.
- Examples: "4.6mg", "2.2mcg", "0.3g", "120IU".
"""

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {
                "role": "system",
                "content": "You provide food nutrition estimates normalized to 100g in structured JSON.",
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format=FoodNutritionResponse,
    )

    parsed = response.choices[0].message.parsed

    protein_g = _to_float(parsed.total_protein_g)
    carbs_g = _to_float(parsed.total_carbs_g)
    fats_g = _to_float(parsed.total_fats_g)

    unit_by_name = {
        "vitamin a": "mcg",
        "vitamin d": "IU",
        "vitamin e": "mg",
        "vitamin k": "mcg",
        "vitamin c": "mg",
        "vitamin b1": "mg",
        "vitamin b2": "mg",
        "vitamin b3": "mg",
        "vitamin b5": "mg",
        "vitamin b6": "mg",
        "vitamin b7": "mcg",
        "vitamin b9": "mcg",
        "vitamin b12": "mcg",
        "calcium": "mg",
        "phosphorus": "mg",
        "magnesium": "mg",
        "sodium": "mg",
        "potassium": "mg",
        "chloride": "mg",
        "sulfur": "mg",
        "iron": "mg",
        "zinc": "mg",
        "copper": "mg",
        "manganese": "mg",
        "iodine": "mcg",
        "selenium": "mcg",
        "fluoride": "mg",
        "chromium": "mcg",
        "molybdenum": "mcg",
    }

    if parsed.micro_nutrients:
        for nutrient in parsed.micro_nutrients:
            amount = str(nutrient.amount).strip()
            if not re.search(r"(mg|mcg|g|iu)$", amount, re.IGNORECASE):
                key = str(nutrient.name).strip().lower()
                unit = unit_by_name.get(key, "mg")
                nutrient.amount = f"{amount}{unit}"

    total_calories = (protein_g * 4) + (carbs_g * 4) + (fats_g * 9)
    parsed.total_calories = str(total_calories)
    return parsed
