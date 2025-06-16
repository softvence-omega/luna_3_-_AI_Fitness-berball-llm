import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import ResponseSchema, StructuredOutputParser, PydanticOutputParser
from app.models.nutrition_schema import NutritionResponse

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
    temperature=0.2,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


response_schemas = [
    ResponseSchema(name="total_protein_g", description="Total protein in grams, (e.g. 140, 35, 10)"),
    ResponseSchema(name="total_carbs_g", description="Total carbohydrates in grams, (e.g. 240, 80)"),
    ResponseSchema(name="total_fats_g", description="Total fats in grams, (e.g., 120, 30, 35)"),
    ResponseSchema(name="total_fiber_g", description="Total fiber in grams, (e.g., 15, 5, 20)")
]

output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
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
                    You are a world-class nutrition expert. Your task is to analyze
                    the attached image of a meal with extreme accuracy.

                    Provide a detailed nutritional breakdown based *only* on the contents
                    of the image.

                    {format_instructions}
                """
    
    user_prompt = f"""
        You are a world-class nutrition expert with expertise in visual food analysis. Your task is to analyze the attached image of a meal with high accuracy and provide a nutritional breakdown for the **entire meal** shown in the image. Do **not** provide per-serving values; calculate totals for all visible food.

        **Requirements**:
        1. Identify all visible food items in the image (e.g., chicken, rice, vegetables).
        2. Estimate the portion sizes or quantities of each food item to calculate totals.
        3. Provide the total grams of protein, carbohydrates, fats, and fiber for the **entire meal** based on standard nutritional data.
        4. Base the analysis only on visible content. Do not assume hidden ingredients or preparation methods (e.g., added oils, sauces) unless clearly visible.
        5. If the image is unclear or ambiguous, provide conservative estimates and note any uncertainties in the calculations.
        6. Do not include a detailed explanation or analysis field in the output; only provide the structured nutritional totals.
        7. If the picture does not contain any food then return default values(set 0(zero) as their default value)

        **Output Example**:
        {{
            "total_protein_g": 40,
            "total_carbs_g": 50,
            "total_fats_g": 16,
            "total_fiber_g": 5,
        }}
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

    print(parsed_response)


    protein_g = int(parsed_response.total_protein_g)
    carbs_g = int(parsed_response.total_carbs_g)
    fats_g = int(parsed_response.total_fats_g)

    total_calories = (protein_g * 4) + (carbs_g * 4) + (fats_g * 9)
    parsed_response.total_calories = str(total_calories)

    return parsed_response