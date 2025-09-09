
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from app.models.workout_schema import WorkoutPlanRequest, WorkoutUpdateRequest, WorkoutPlan


llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)


parser = PydanticOutputParser(pydantic_object=WorkoutPlan)
format_instructions = parser.get_format_instructions()


async def generate_workout_plan(request: WorkoutPlanRequest) -> dict:
    """
    Generates a workout plan based on user details.

    Args:
        request: A Pydantic model containing the user's details and preferences.

    Returns:
        A dictionary representing the generated workout plan.
    """
    prompt = f"""
        You are a world-class personal trainer and fitness expert. Your task is to create a safe, effective, and highly personalized workout plan based on the user's details.

        **User Details:**
        - Age: {request.age}
        - Gender: {request.gender}
        - Weight: {request.weight_kg} kg
        - Height: {request.height_cm} cm
        - Fitness Level: {request.fitness_level}
        - Main Goal: {request.main_goal}
        - Training Days per Week: {request.days_per_week}
        - Available Equipment: {request.available_equipment}
        - Additional Notes: {request.notes or 'None'}

        Based on these details, create a structured workout plan for the specified number of days.
        The plan should be a weekly schedule. For each workout day, specify the main focus (e.g., 'Upper Body', 'Leg Day') and provide a list of exercises with sets, reps, and rest periods.
        Ensure the exercises are appropriate for the user's fitness level and available equipment.
        Pay close attention to any notes, especially regarding injuries.

        {format_instructions}
    """

    messages = [
        SystemMessage(content="You are an expert AI personal trainer creating a JSON workout plan."),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    parsed_plan = parser.parse(response.content)

    return {"workout_plan": parsed_plan.dict()}


async def refine_workout_plan(request: WorkoutUpdateRequest) -> dict:
    """
    Refines an existing workout plan based on user feedback.

    Args:
        request: A Pydantic model containing the original plan and user feedback.

    Returns:
        A dictionary representing the updated workout plan.
    """
    prompt = f"""
       You are an expert personal trainer acting as a long-term coach. Your task is to analyze user feedback and decide on the correct course of action.

        **CRITICAL INSTRUCTIONS:**
        1.  **Analyze Intent:** First, read the user's feedback carefully to understand what they mean.
        2.  **Make a Decision:**
            -   If the user's feedback **asks for a change** (e.g., "this is too hard," "add more bicep work," "let's progress"), you MUST modify the most recent plan. 
            -   If the user's feedback expresses **satisfaction and does NOT ask for a change** (e.g., "great!", "this was perfect", "loved it"), you MUST NOT change the plan. 


        **Original Workout Plan:**
        ```json
        {request.original_plan.json()}
        ```

        **User's Feedback:**
        "{request.feedback}"

        Based on the feedback, please modify the original workout plan.
        - Analyze the user's feedback carefully.
        - Make specific, logical changes to the plan. This could mean adjusting volume, swapping exercises, changing the focus of a day, etc.
        - Return the COMPLETE, updated workout plan in the same structured format as the original. Do not just describe the changes.

        {format_instructions}
    """

    messages = [
        SystemMessage(content="You are an expert AI personal trainer updating a JSON workout plan based on feedback."),
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    updated_plan = parser.parse(response.content)

    return {"workout_plan": updated_plan.dict()}
