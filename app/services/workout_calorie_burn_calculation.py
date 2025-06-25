from app.models.workout_schema import ExerciseRequest, CalorieResponse
# import groq
import json
import os
from datetime import datetime
import dotenv
# NOTE: Ensure the 'openai' package is installed in your environment: pip install openai
import openai
import re

dotenv.load_dotenv()

# OpenAI client setup
openai.api_key = os.getenv("OPENAI_API_KEY")

def calculate_calories_with_openai(exercise_data: ExerciseRequest) -> dict:
    """
    Use OpenAI API to calculate calories burned based on exercise data.
    
    Args:
        exercise_data (ExerciseRequest): Object containing exercise details.
    
    Returns:
        dict: Calorie calculation results in JSON format.
    """
    # Input validation
    if exercise_data.body_weight <= 0:
        raise ValueError("Body weight must be greater than zero")
    if exercise_data.reps <= 0:
        raise ValueError("Reps must be greater than zero")

    # Calculate weight intensity ratio for context
    weight_ratio = exercise_data.weightLifted / exercise_data.body_weight if exercise_data.weightLifted > 0 else 0
    weight_percentage = round(weight_ratio * 100, 1)
    avg_time_per_rep = exercise_data.rep_duration / exercise_data.reps

    # Prepare the enhanced prompt for OpenAI
    prompt = f"""
    You are a fitness expert calculating calories burned. Use your knowledge of exercise physiology and specific exercises to provide accurate calorie calculations.

    User Information:
    - Body weight: {exercise_data.body_weight} kg
    - Height: {exercise_data.height} feet

    Exercise Details:
    - Exercise: {exercise_data.exerciseName}
    - Type: {exercise_data.exerciseType}
    - Weight lifted: {exercise_data.weightLifted} kg
    - Repetitions: {exercise_data.reps}
    - Sets: {exercise_data.sets}
    - Rep duration: {exercise_data.rep_duration} seconds total ({round(avg_time_per_rep, 1)} seconds per rep)
    - Rest time: {exercise_data.restTime} seconds between sets

    EXERCISE-SPECIFIC CALCULATION REQUIREMENTS:

    1. EXERCISE-SPECIFIC BASE MET VALUES - Different exercises burn different calories:
       
       UPPER BODY (Lower calorie burn):
       - Bicep curls, tricep extensions: 2.5-3.0 MET
       - Shoulder press, lateral raises: 3.0-3.5 MET
       - Bench press, rows: 3.5-4.0 MET
       
       LOWER BODY (Higher calorie burn):
       - Leg press, squats: 4.5-5.5 MET
       - Lunges, step-ups: 5.0-6.0 MET
       - Deadlifts: 5.5-6.5 MET
       
       COMPOUND MOVEMENTS (Highest calorie burn):
       - Burpees, thrusters: 6.0-8.0 MET
       - Olympic lifts: 6.5-8.5 MET
       - Full-body circuits: 7.0-9.0 MET

    2. MUSCLE GROUP ENGAGEMENT FACTOR:
       - Single small muscle (bicep curl): Base MET
       - Multiple small muscles (tricep dips): +20% MET
       - Large muscle groups (leg press): +60-80% MET
       - Multiple large muscles (squats): +100-120% MET
       - Full body compound (deadlift): +150-200% MET

    3. WEIGHT AND INTENSITY ADJUSTMENTS:
       - Weight factor = 1.0 + (weight_lifted_kg × 0.02)
       - Rep speed factor: Slower reps = higher calories
         * Very slow (5+ sec/rep): +40%
         * Slow (3-5 sec/rep): +25%
         * Normal (2-3 sec/rep): Base
         * Fast (<2 sec/rep): -15%

    4. REST TIME LIMITATION:
       - Rest calories = min(1.3 MET × body_weight × rest_hours, working_calories × 0.2)

    5. EXAMPLES FOR REFERENCE:
       - Bicep curls 15kg vs Leg press 100kg (same person): Leg press burns 2-3x more
       - Tricep extensions vs Squats (same weight): Squats burn 60-80% more
       - Isolated movements vs Compound movements: Compound burns significantly more

    CALCULATION STEPS:
    1. Identify the specific exercise and determine appropriate base MET
    2. Apply muscle group engagement multiplier
    3. Apply weight factor and rep speed factor
    4. Calculate working calories using exercise-specific MET
    5. Add minimal rest calories (capped)

    Provide response in JSON format:
    {{
        "total_calories_burned": <number>,
        "calories_per_set": <number>,
        "total_exercise_time_seconds": <number>,
        "calculation_method": "<explain exercise-specific MET and muscle group factors>",
        "metabolic_equivalent": <final exercise-specific MET>,
        "reasoning": "<explain why this exercise burns more/less calories than others and how factors were applied>",
        "exercise_category": "<small_muscle/large_muscle/compound/full_body>",
        "muscle_groups_engaged": "<list primary muscle groups>"
    }}
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

        # Parse the response
        content = response.choices[0].message.content

        # Try parsing the entire content as JSON first
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # If that fails, extract JSON using regex
            json_match = re.search(r'\{.*\}', content or '', re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
            else:
                print("No valid JSON found in OpenAI response")
                return fallback_calculation(exercise_data)

        # Validate required keys
        required_keys = ["total_calories_burned", "calories_per_set", "total_exercise_time_seconds"]
        if not all(key in result for key in required_keys):
            print("Invalid JSON format from OpenAI")
            return fallback_calculation(exercise_data)

        return result

    except Exception as e:
        print(f"OpenAI API error: {e}")
        return fallback_calculation(exercise_data)

def fallback_calculation(exercise_data: ExerciseRequest) -> dict:
    """
    Enhanced fallback calculation with exercise-specific MET values.
    
    Args:
        exercise_data (ExerciseRequest): Object containing exercise details.
    
    Returns:
        dict: Calorie calculation results.
    """
    # Input validation
    if exercise_data.body_weight <= 0:
        raise ValueError("Body weight must be greater than zero")
    if exercise_data.reps <= 0:
        raise ValueError("Reps must be greater than zero")

    # Get exercise-specific base MET
    base_met = get_exercise_specific_met(exercise_data.exerciseName, exercise_data.exerciseType)

    # Weight-based calorie adjustment
    if exercise_data.weightLifted > 0:
        weight_factor = 1.0 + (exercise_data.weightLifted * 0.02)  # 2% increase per kg
        weight_ratio = exercise_data.weightLifted / exercise_data.body_weight
        if weight_ratio > 0.5:  # If lifting more than 50% of body weight
            weight_factor *= (1.0 + (weight_ratio - 0.5) * 0.5)  # Additional 50% boost
    else:
        weight_factor = 1.0

    # Rep speed adjustment
    avg_time_per_rep = exercise_data.rep_duration / exercise_data.reps
    if avg_time_per_rep >= 5.0:
        speed_factor = 1.4  # 40% more calories
    elif avg_time_per_rep >= 3.0:
        speed_factor = 1.25  # 25% more calories
    elif avg_time_per_rep >= 2.0:
        speed_factor = 1.0  # Base calories
    else:
        speed_factor = 0.85  # 15% fewer calories

    # Calculate work-based MET adjustment
    work_volume = exercise_data.reps * exercise_data.sets * max(exercise_data.weightLifted, exercise_data.body_weight * 0.1)
    volume_factor = 1.0 + (work_volume * 0.00005)  # Small boost for high volume

    # Final MET calculation
    final_met = base_met * weight_factor * speed_factor * volume_factor

    # Calculate total exercise time
    total_working_time = exercise_data.rep_duration * exercise_data.sets
    total_rest_time = exercise_data.restTime * (exercise_data.sets - 1) if exercise_data.sets > 1 else 0

    # Rest calories (capped)
    rest_calories_raw = (1.3 * exercise_data.body_weight * (total_rest_time / 3600))
    working_time_hours = total_working_time / 3600
    working_calories = final_met * exercise_data.body_weight * working_time_hours
    max_rest_calories = working_calories * 0.2
    rest_calories = min(rest_calories_raw, max_rest_calories)

    total_calories = working_calories + rest_calories
    calories_per_set = working_calories / exercise_data.sets if exercise_data.sets > 0 else 0
    total_session_time = total_working_time + total_rest_time

    # Determine exercise category
    exercise_category = "unknown"
    if base_met <= 3.2:
        exercise_category = "small_muscle_isolation"
    elif base_met <= 4.5:
        exercise_category = "large_muscle_isolation"
    elif base_met <= 6.0:
        exercise_category = "compound_movement"
    else:
        exercise_category = "full_body_high_intensity"

    return {
        "total_calories_burned": round(total_calories, 2),
        "calories_per_set": round(calories_per_set, 2),
        "total_exercise_time_seconds": total_session_time,
        "calculation_method": f"Exercise-specific calculation: {exercise_data.exerciseName} (Base MET: {base_met}) × Weight factor: {round(weight_factor, 2)} × Speed factor: {round(speed_factor, 2)}",
        "metabolic_equivalent": round(final_met, 2),
        "reasoning": f"Exercise-specific MET: {base_met} for {exercise_data.exerciseName}. Weight: {exercise_data.weightLifted}kg increases calories by {round((weight_factor-1)*100, 1)}%. Rep speed: {round(avg_time_per_rep, 1)}s/rep {'increases' if speed_factor > 1 else 'decreases'} calories by {round(abs(speed_factor-1)*100, 1)}%",
        "exercise_category": exercise_category,
        "muscle_groups_engaged": "Based on exercise type and movement pattern"
    }

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

