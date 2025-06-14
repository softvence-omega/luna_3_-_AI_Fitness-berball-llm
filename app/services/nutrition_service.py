import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import ResponseSchema, StructuredOutputParser


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

    messages = [
        SystemMessage(content="You are an AI nutritionist that provides nutritional information from images."),
        HumanMessage(content=[
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ])
    ]

    response = llm.invoke(messages)
    parsed_response = output_parser.parse(response.content)


    protein_g = int(parsed_response.get('total_protein_g', 0))
    carbs_g = int(parsed_response.get('total_carbs_g', 0))
    fats_g = int(parsed_response.get('total_fats_g', 0))

    total_calories = (protein_g * 4) + (carbs_g * 4) + (fats_g * 9)
    parsed_response['total_calories'] = str(total_calories)

    return parsed_response