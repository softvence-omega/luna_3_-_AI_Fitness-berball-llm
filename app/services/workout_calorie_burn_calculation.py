from app.models.workout_schema import ExerciseRequest, CalorieResponse
# import groq
import json
import os
from datetime import datetime
import dotenv
# NOTE: Ensure the 'openai' package is installed in your environment: pip install openai
import openai
import re
from typing import Dict, Any

dotenv.load_dotenv()

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
    - Height: {user_height} cm

    Exercise Details:
    - Exercise: {exercise_name}
    - Type: {exercise_type}
    """
    if weight_lifted:
        prompt += f"- Weight lifted: {weight_lifted} kg\n"
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

    prompt += """
    
    Please use exercise-specific MET values and adjust for intensity, weight, and rest as appropriate. If any field is missing, make a reasonable assumption. For cardio, ignore weight lifted and reps if not provided. For weight training, use all available data. If the user hits failure in every set or performs explosively, increase the calorie estimate accordingly.

    Provide response in JSON format:
    {
        "total_calories_burned": <number>,
        "calories_per_set": <number>,
        "total_exercise_time_seconds": <number>,
        "calculation_method": "<explain exercise-specific MET and muscle group factors>",
        "metabolic_equivalent": <final exercise-specific MET>,
        "reasoning": "<explain why this exercise burns more/less calories than others and how factors were applied>",
        "exercise_category": "<small_muscle/large_muscle/compound/full_body>",
        "muscle_groups_engaged": "<list primary muscle groups>"
    }
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a fitness expert specializing in calorie calculations. Provide accurate, science-based calorie burn estimates using MET values and established formulas."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        content = response.choices[0].message.content
        # Try parsing the entire content as JSON first
        try:
            result = json.loads(content or "{}")
        except json.JSONDecodeError:
            # If that fails, extract JSON using regex
            json_match = re.search(r'\{.*\}', content or '', re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in OpenAI response")

        # Validate required keys
        required_keys = ["total_calories_burned", "calories_per_set", "total_exercise_time_seconds"]
        if not all(key in result for key in required_keys):
            raise ValueError("Invalid JSON format from OpenAI")

        return result

    except Exception as e:
        return {"error": f"OpenAI API error or invalid response: {e}"}

def get_exercise_specific_met(exercise_name: str, exercise_type: str) -> float:
    """
    Get exercise-specific MET values based on muscle groups engaged.
    
    Args:
        exercise_name (str): Name of the exercise.
        exercise_type (str): Type of the exercise (e.g., cardio, strength).
    
    Returns:
        float: MET value for the exercise.
    """
    exercise_lower = exercise_name.lower()

    # Exercise-specific MET database
    exercise_mets = {
        'bicep curl': 2.8, 'bicep curls': 2.8, 'tricep extension': 2.8, 'tricep curls': 2.8,
        'lateral raise': 3.0, 'shoulder raise': 3.0, 'chest fly': 3.2, 'hammer curl': 2.8,
        'bench press': 3.8, 'push up': 3.8, 'pushup': 3.8, 'pull up': 4.2, 'pullup': 4.2,
        'row': 3.5, 'rowing': 3.5, 'shoulder press': 3.5, 'military press': 3.8, 'chest press': 3.8,
        'squat': 5.0, 'squats': 5.0, 'leg press': 4.8, 'lunge': 5.2, 'lunges': 5.2,
        'leg curl': 3.5, 'leg extension': 3.5, 'calf raise': 3.0, 'leg raise': 4.0,
        'deadlift': 6.0, 'deadlifts': 6.0, 'clean': 6.5, 'snatch': 7.0, 'thruster': 6.8,
        'burpee': 7.5, 'burpees': 7.5, 'mountain climber': 7.0, 'jumping jack': 6.5,
        'kettlebell swing': 6.0, 'battle rope': 7.2, 'box jump': 6.8
    }

    # Try exact match
    if exercise_lower in exercise_mets:
        return exercise_mets[exercise_lower]

    # Try partial matching
    for exercise_key, met_value in exercise_mets.items():
        if exercise_key in exercise_lower or any(word in exercise_lower for word in exercise_key.split()):
            return met_value

    # Fallback to exercise type
    type_mets = {
        'cardio': 6.0, 'strength': 3.5, 'weightlifting': 3.5, 'resistance': 3.5,
        'compound': 5.5, 'isolation': 3.0
    }
    return type_mets.get(exercise_type.lower(), 4.0)

