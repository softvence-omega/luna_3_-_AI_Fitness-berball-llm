import base64
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import  PydanticOutputParser
from app.models.nutrition_schema import NutritionResponse
from langchain_openai import ChatOpenAI
from app.config.settings import OPENAI_API_KEY


llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=OPENAI_API_KEY
)


output_parser = PydanticOutputParser(pydantic_object = NutritionResponse) 
format_instructions = output_parser.get_format_instructions()


async def get_nutritional_analysis(image_bytes: bytes) -> dict:
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
    You are a world-class nutrition expert with expertise in visual food analysis. Your task is to analyze the attached image of a meal with high accuracy and provide a nutritional breakdown for the **entire meal** shown in the image. Do **not** provide per-serving values; calculate totals for all visible food.

    **Requirements**:
    1. Identify all visible food items in the image (e.g., chicken, rice, vegetables).
    2. Estimate the portion sizes or quantities of each food item to calculate totals.
    3. Provide the total grams of protein, carbohydrates, fats, and fiber for the **entire meal** based on standard nutritional data.
    4. Include ALL micronutrients (vitamins and minerals) that are present in the visible foods. List every vitamin and mineral found in the meal, including:
       - **Vitamins**: A, D, E, K, C, B1 (Thiamine), B2 (Riboflavin), B3 (Niacin), B5 (Pantothenic Acid), B6 (Pyridoxine), B7 (Biotin), B9 (Folate), B12 (Cobalamin)
       - **Minerals**: Calcium, Phosphorus, Magnesium, Sodium, Potassium, Chloride, Sulfur, Iron, Zinc, Copper, Manganese, Iodine, Selenium, Fluoride, Chromium, Molybdenum
       Only include micronutrients that are actually present in the identified foods with their estimated amounts. If not present to a significant degree, do not list them.
    5. Base the analysis only on visible content. Do not assume hidden ingredients or preparation methods (e.g., added oils, sauces) unless clearly visible.
    6. If the image is unclear or ambiguous, provide conservative estimates and note any uncertainties in the calculations.
    7. Do not include a detailed explanation or analysis field in the output; only provide the structured nutritional totals.
    8. If the picture does not contain any food then return default values (set 0 (zero) as their default value for macronutrients and an empty array for micronutrients).


    {format_instructions}
    """

    messages = [
        SystemMessage(content="You are an AI nutritionist specializing in analyzing food images to provide accurate nutritional information."),
        HumanMessage(content=[
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ])
    ]

    response = llm.invoke(messages)
    parsed_response = output_parser.parse(response.content)



    protein_g = int(parsed_response.total_protein_g)
    carbs_g = int(parsed_response.total_carbs_g)
    fats_g = int(parsed_response.total_fats_g)

    total_calories = (protein_g * 4) + (carbs_g * 4) + (fats_g * 9)
    parsed_response.total_calories = str(total_calories)

    return parsed_response



    """
        # **Output Example**:
    # {{
    #     "total_protein_g": "40",
    #     "total_carbs_g": "50",
    #     "total_fats_g": "16",
    #     "total_fiber_g": "5",
    #     "micro_nutrients": [
    #         {{
    #             "name": "Vitamin A",
    #             "amount": "500 mcg"
    #         }},
    #         {{
    #             "name": "Vitamin C",
    #             "amount": "25 mg"
    #         }},
    #         {{
    #             "name": "Vitamin D",
    #             "amount": "2 mcg"
    #         }},
    #         {{
    #             "name": "Vitamin E",
    #             "amount": "1.5 mg"
    #         }},
    #         {{
    #             "name": "Vitamin K",
    #             "amount": "15 mcg"
    #         }},
    #         {{
    #             "name": "Vitamin B1 (Thiamine)",
    #             "amount": "0.3 mg"
    #         }},
    #         {{
    #             "name": "Vitamin B2 (Riboflavin)",
    #             "amount": "0.4 mg"
    #         }},
    #         {{
    #             "name": "Vitamin B3 (Niacin)",
    #             "amount": "8 mg"
    #         }},
    #         {{
    #             "name": "Vitamin B6 (Pyridoxine)",
    #             "amount": "0.5 mg"
    #         }},
    #         {{
    #             "name": "Vitamin B9 (Folate)",
    #             "amount": "80 mcg"
    #         }},
    #         {{
    #             "name": "Vitamin B12 (Cobalamin)",
    #             "amount": "1.2 mcg"
    #         }},
    #         {{
    #             "name": "Calcium",
    #             "amount": "150 mg"
    #         }},
    #         {{
    #             "name": "Iron",
    #             "amount": "3.5 mg"
    #         }},
    #         {{
    #             "name": "Magnesium",
    #             "amount": "80 mg"
    #         }},
    #         {{
    #             "name": "Phosphorus",
    #             "amount": "250 mg"
    #         }},
    #         {{
    #             "name": "Potassium",
    #             "amount": "600 mg"
    #         }},
    #         {{
    #             "name": "Sodium",
    #             "amount": "400 mg"
    #         }},
    #         {{
    #             "name": "Zinc",
    #             "amount": "4 mg"
    #         }},
    #         {{
    #             "name": "Copper",
    #             "amount": "0.5 mg"
    #         }},
    #         {{
    #             "name": "Manganese",
    #             "amount": "1 mg"
    #         }},
    #         {{
    #             "name": "Selenium",
    #             "amount": "30 mcg"
    #         }}
    #     ],
    #     "total_calories": "520"
    # }}
    """