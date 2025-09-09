import os
from dotenv import load_dotenv
import openai
from typing import Dict, Any, Literal, List
from langchain.output_parsers import  PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

load_dotenv()



class ExerciseCalorieResponse(BaseModel):
    total_calories_burned: float = Field(..., description="Total calories burned during the exercise session")
    calories_per_set: float = Field(..., description="Calories burned per set of the exercise")
    total_exercise_time_seconds: int = Field(..., description="Total duration of the exercise in seconds")
    calculation_method: str = Field(..., description="Explanation of how MET and muscle group factors were used in the calculation")
    metabolic_equivalent: float = Field(..., description="Final MET value specific to the exercise")
    reasoning: str = Field(..., description="Explanation of why this exercise burns more or fewer calories compared to others")
    exercise_category: Literal["small_muscle", "large_muscle", "compound", "full_body"] = Field(..., description="Category of the exercise based on muscle engagement")
    muscle_groups_engaged: List[str] = Field(..., description="List of primary muscle groups targeted by the exercise")


llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.4,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=os.getenv("OPENAI_API_KEY")
)

output_parser = PydanticOutputParser(pydantic_object = ExerciseCalorieResponse) 
format_instructions = output_parser.get_format_instructions()



# OpenAI client setup
openai.api_key = os.getenv("OPENAI_API_KEY")

def calculate_calories_with_openai(exercise_data: Dict[str, Any]) -> dict:
    """
    Use OpenAI API to calculate calories burned based on exercise data from API input.
    Args:
        exercise_data (dict): Dictionary containing exercise details from API.
    Returns:
        dict: Calorie calculation results in JSON format.
    """
    # Extract and handle fields with defaults for missing/optional
    user_height = exercise_data.get("userHight")
    user_weight = exercise_data.get("userWeight")
    exercise_name = exercise_data.get("exerciseName", "")
    exercise_type = exercise_data.get("exerciseType", "")
    exercise_description = exercise_data.get("exerciseDescription", "")
    weight_lifted = exercise_data.get("weightLifted", 0)
    reps = exercise_data.get("reps", 0)
    sets = exercise_data.get("set", 0)
    reset_time = exercise_data.get("resetTime", 0)
    restime = exercise_data.get("restime", None)

    # Input validation (basic)
    if not user_weight or user_weight <= 0:
        raise ValueError("User weight must be provided and greater than zero.")
    if not user_height or user_height <= 0:
        raise ValueError("User height must be provided and greater than zero.")
    if not exercise_name:
        raise ValueError("Exercise name must be provided.")

    # Prepare prompt parts based on available data
    prompt = f"""
    You are a fitness expert calculating calories burned. Use your knowledge of exercise physiology and specific exercises to provide accurate calorie calculations.

    User Information:
    - Body weight: {user_weight} kg
    - Height: {user_height} feet.inches (convert to cm)

    Exercise Details:
    - Exercise: {exercise_name}
    - Type: {exercise_type}
    """
    if weight_lifted:
        prompt += f"- Weight lifted: {weight_lifted} lb\n"
    if reps:
        prompt += f"- Repetitions: {reps}\n"
    if sets:
        prompt += f"- Sets: {sets}\n"
    if reset_time:
        prompt += f"- Set/Session duration: {reset_time} seconds\n"
    if restime:
        prompt += f"- Rest time between sets: {restime} seconds\n"
    if exercise_description:
        prompt += f"- Additional info: {exercise_description}\n"

    prompt += f"""

    Please use exercise-specific MET values and adjust for intensity, weight, and rest as appropriate. If any field is missing, make a reasonable assumption. For cardio, ignore weight lifted and reps if not provided. For weight training, use all available data. If the user hits failure in every set or performs explosively, increase the calorie estimate accordingly.

    Provide response in JSON format:

    {format_instructions}

    """
    try:
        messages = [
        SystemMessage(content="You are a fitness expert specializing in calorie calculations. Provide accurate, science-based calorie burn estimates using MET values and established formulas."),
        HumanMessage(content=[
            {"type": "text", "text": prompt}
        ])
    ]
        response = llm.invoke(messages)
        parsed_response = output_parser.parse(response.content)


        return {
            "total_calories_burned": parsed_response.total_calories_burned,
            "calories_per_set": parsed_response.calories_per_set,
            "total_exercise_time_seconds": parsed_response.total_exercise_time_seconds,
            "calculation_method": parsed_response.calculation_method,
            "metabolic_equivalent": parsed_response.metabolic_equivalent,
            "reasoning": parsed_response.reasoning,
            "exercise_category": parsed_response.exercise_category,
            "muscle_groups_engaged": parsed_response.muscle_groups_engaged
            }

    except Exception as e:
        return {"error": f"OpenAI API error or invalid response: {e}"}


