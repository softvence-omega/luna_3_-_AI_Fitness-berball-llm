from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.output_parsers import PydanticOutputParser
import base64

from app.config.settings import OPENAI_API_KEY

class IngredientListResponse(BaseModel):
    food_name: str = Field(description="Name of the food identified in the image")
    ingredients: List[str] = Field(description="List of ingredients the food is made of or contains")

llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=OPENAI_API_KEY
)

async def scan_ingredients(image_bytes: bytes) -> IngredientListResponse:
    output_parser = PydanticOutputParser(pydantic_object=IngredientListResponse)
    format_instructions = output_parser.get_format_instructions()
    
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    data_uri = f"data:image/jpeg;base64,{image_data}"
    
    user_prompt = f"""
    You are an expert culinary and food scientist. Your task is to analyze the provided image of food and identify what it is and what ingredients it is made of.
    
    The food can be:
    - Raw or cooked dishes (e.g., Pizza, Salad, Steak)
    - Packaged foods (e.g., a bag of chips, a bottle of soda)
    - Fresh produce or simple ingredients
    
    Identify the food name and provide a comprehensive list of ingredients. For packaged foods, if the ingredients list is visible, use it. For prepared dishes, use your expertise to list the likely ingredients.
    
    {format_instructions}
    """

    messages = [
        SystemMessage(content="You are an AI specialized in food identification and ingredient analysis."),
        HumanMessage(content=[
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_uri}},
        ])
    ]

    response = llm.invoke(messages)
    parsed_response = output_parser.parse(response.content)
    
    return parsed_response
