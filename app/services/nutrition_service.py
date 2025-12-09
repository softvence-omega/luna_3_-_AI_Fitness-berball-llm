import base64
from app.models.nutrition_schema import NutritionResponse
from app.config.settings import OPENAI_API_KEY


from openai import OpenAI
client = OpenAI(
    api_key=OPENAI_API_KEY
)



async def get_nutritional_analysis(image_bytes: bytes) -> NutritionResponse:
    """
    Analyzes an image of a meal to determine its nutritional content.

    Args:
        image_bytes: The byte content of the image file.

    Returns:
        A dictionary containing the nutritional breakdown (protein, carbs, fats, fiber, calories).
    """

    image_data = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{image_data}"
    
    user_prompt = f"""
    You are a world-class nutrition expert with expertise in visual food analysis and nutrition label reading. Your task is to analyze the attached image and provide a nutritional breakdown.

    **Image Analysis Priority**:
    1. **First, check if there is a visible nutrition facts label** (on packaging, bottles, boxes, etc.)
       - If YES: Read the nutrition label carefully and extract all information
       - Calculate totals for the ENTIRE PACKAGE (multiply per-serving values by number of servings if needed)
       - Use the label data as your primary source of truth
    
    2. **If no nutrition label is visible OR if there are loose/prepared food items**:
       - Identify all visible food items in the image
       - Estimate portion sizes and quantities
       - Provide nutritional totals based on standard nutritional data

    **Requirements for ALL cases**:
    1. Provide total grams of protein, carbohydrates, fats, and fiber for the **entire meal/package**
    2. Include ALL micronutrients (vitamins and minerals) present:
       - **Vitamins**: A, D, E, K, C, B1 (Thiamine), B2 (Riboflavin), B3 (Niacin), B5 (Pantothenic Acid), B6 (Pyridoxine), B7 (Biotin), B9 (Folate), B12 (Cobalamin)
       - **Minerals**: Calcium, Phosphorus, Magnesium, Sodium, Potassium, Chloride, Sulfur, Iron, Zinc, Copper, Manganese, Iodine, Selenium, Fluoride, Chromium, Molybdenum
       - Only include micronutrients that are present in significant amounts
    3. For packaged foods, if micronutrients are listed on the label, include them. If not listed, estimate based on the food type.
    4. Do not assume hidden ingredients unless clearly visible or stated on the label
    5. If the image contains BOTH packaged food AND loose items, analyze whichever is more prominent/clear
    6. If unclear, provide conservative estimates and note uncertainties
    7. Do not include detailed explanations; only provide structured nutritional totals
    8. If the image does not contain any food or nutrition label, return default values (0 for macronutrients, empty array for micronutrients)

    **For Packaged Foods Specifically**:
    - Read serving size and servings per container
    - Calculate: Total = (Per Serving Value) × (Servings Per Container)
    - Extract micronutrients if listed (often shown as % Daily Value)
    - Convert % Daily Value to actual amounts when possible

    **Output Format**:
    - Total protein in grams
    - Total carbohydrates in grams
    - Total fats in grams
    - Total fiber in grams
    - List of micronutrients with their amounts
    - Total calories in kcal

    **Example**:
        **Example Output Format**:
    {{
        "total_protein_g": "7.3",
        "total_carbs_g": "67.3",
        "total_fats_g": "13.5",
        "total_fiber_g": "3.1",
        "micro_nutrients": [
            {{"name": "micro-nutrient-name", "amount": "value with unit"}},
        ],
        "total_calories": "447"
    }}

    CRITICAL: DO NOT USE UNIT IN RESPONSES LIKE MG OR G IN THE VALUES. ONLY PROVIDE NUMBERS AS STRINGS.
    """

    response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are an AI nutritionist specializing in analyzing food images and reading nutrition labels to provide accurate nutritional information."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri,
                                "detail": "high"
                            }
                        },
                    ],
                },
            ],
            temperature=0,
            response_format=NutritionResponse,
        )

    parsed = response.choices[0].message.parsed

    protein_g = float(parsed.total_protein_g)
    carbs_g = float(parsed.total_carbs_g)
    fats_g = float(parsed.total_fats_g)

    total_calories = (protein_g * 4) + (carbs_g * 4) + (fats_g * 9)
    parsed.total_calories = str(total_calories)
    return parsed

