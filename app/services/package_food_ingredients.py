from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.output_parsers import PydanticOutputParser
import base64

from app.config.settings import OPENAI_API_KEY

# Pydantic models for packaged food analysis
class Ingredient(BaseModel):
    name: str = Field(description="Name of the ingredient")
    measurement: Optional[str] = Field(description="Measurement/quantity of the ingredient if available", default=None)

class MicroNutrient(BaseModel):
    name: str = Field(description="Name of the micronutrient (vitamin or mineral)")
    amount: str = Field(description="Amount of the micronutrient with unit")

class PackagedFoodResponse(BaseModel):
    product_name: str = Field(description="Name of the product from the package")
    ingredients: List[Ingredient] = Field(description="List of all ingredients found on the package")
    total_protein_g: str = Field(description="Total protein in grams")
    total_carbs_g: str = Field(description="Total carbohydrates in grams")
    total_fats_g: str = Field(description="Total fats in grams")
    total_fiber_g: str = Field(description="Total fiber in grams")
    micro_nutrients: List[MicroNutrient] = Field(description="List of micronutrients (vitamins and minerals)")
    total_calories: str = Field(description="Total calories")

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=OPENAI_API_KEY
)

async def scan_packaged_food(image_bytes: bytes) -> PackagedFoodResponse:
    output_parser = PydanticOutputParser(pydantic_object=PackagedFoodResponse)
    format_instructions = output_parser.get_format_instructions()
    
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{image_data}"
    
    user_prompt = f"""
    You are an expert at reading and analyzing packaged food labels. Your task is to extract ALL information from the food package image, including:

    **1. Product Information:**
    - Product name
    - Serving size

    **2. Ingredients List:**
    - Extract ALL ingredients listed on the package
    - Include measurements/quantities if they are specified next to ingredients
    - Maintain the order as listed on the package
    - If no ingredients list is visible, return an empty array

    **3. Nutrition Facts:**
    - Total calories
    - Protein (in grams)
    - Total carbohydrates (in grams)
    - Total fats (in grams)
    - Dietary fiber (in grams)
    
    **4. Micronutrients:**
    - Extract ALL vitamins and minerals listed in the Nutrition Facts panel
    - Include the amount with proper units (mg, mcg, IU, % Daily Value, etc.)
    - Common micronutrients include: Vitamin A, C, D, E, K, B vitamins, Calcium, Iron, Potassium, Sodium, Magnesium, Zinc, etc.

    **Important Guidelines:**
    - Extract data EXACTLY as shown on the package label
    - If certain fields are not visible or not applicable, use empty strings or null values
    - Be precise with units (g, mg, mcg, IU, etc.)
    - Read carefully to distinguish between similar nutrients (e.g., "Total Fat" vs "Saturated Fat")

    {format_instructions}
    """

    messages = [
        SystemMessage(content="You are an AI specialized in reading and extracting information from food package labels and nutrition facts panels."),
        HumanMessage(content=[
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ])
    ]

    response = llm.invoke(messages)
    parsed_response = output_parser.parse(response.content)

    print("Packaged Food Scan Response:", parsed_response)
    
    return parsed_response


# Optional: Function to get total package nutrition (multiply by servings)
async def get_total_package_nutrition(image_bytes: bytes) -> dict:
    """
    Gets the total nutritional content for the entire package.
    
    Args:
        image_bytes: The byte content of the image file showing the food package.
    
    Returns:
        A dictionary with total nutritional values for the entire package.
    """
    per_serving = await scan_packaged_food(image_bytes)
    
    try:
        servings = float(per_serving.servings_per_container) if per_serving.servings_per_container else 1.0
        
        return {
            "product_name": per_serving.product_name,
            "total_for_package": {
                "total_protein_g": str(float(per_serving.total_protein_g) * servings),
                "total_carbs_g": str(float(per_serving.total_carbs_g) * servings),
                "total_fats_g": str(float(per_serving.total_fats_g) * servings),
                "total_fiber_g": str(float(per_serving.total_fiber_g) * servings),
                "total_calories": str(float(per_serving.total_calories) * servings),
            },
            "per_serving": per_serving,
            "servings_per_container": servings
        }
    except (ValueError, TypeError):
        return {"error": "Could not calculate total package nutrition", "per_serving_data": per_serving}