from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator, field_validator
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid
import asyncio
from typing import Dict, Optional
from fastapi.middleware.cors import CORSMiddleware
from app.api.mealplan_router import router as mealplan_router
from app.config.settings import OPENAI_API_KEY, OPENAI_API_URL

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://luna3server.onrender.com/api/v1", "http://127.0.0.1:8000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# In-memory storage for responses (simulating database)
response_storage = {}

# New structure for user and session management
user_sessions: Dict[str, Dict[str, 'ChatSession']] = {}

# Session configuration
SESSION_TIMEOUT = 3600  # 1 hour in seconds
MAX_SESSIONS_PER_USER = 5
MAX_MESSAGES_PER_SESSION = 50
CLEANUP_INTERVAL = 300  # 5 minutes in seconds

class ChatSession:
    def __init__(self, user_id: Optional[str] = None):
        self.history = []
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.message_count = 0

    def add_message(self, role: str, content: str) -> bool:
        if self.message_count >= MAX_MESSAGES_PER_SESSION:
            return False
        
        self.history.append({"role": role, "content": content})
        self.last_activity = datetime.utcnow()
        self.message_count += 1
        return True

    def get_history(self):
        return self.history

    def is_expired(self) -> bool:
        return (datetime.utcnow() - self.last_activity).total_seconds() > SESSION_TIMEOUT

    def clear(self):
        self.history = []
        self.message_count = 0

async def cleanup_all_sessions():
    while True:
        try:
            current_time = datetime.utcnow()
            
            # Clean up expired sessions for each user
            for user_id in list(user_sessions.keys()):
                user_session_dict = user_sessions[user_id]
                
                # Remove expired sessions
                expired_sessions = [
                    session_id for session_id, session in user_session_dict.items()
                    if session.is_expired()
                ]
                for session_id in expired_sessions:
                    del user_session_dict[session_id]
                
                # If user has no sessions left, remove the user entry
                if not user_session_dict:
                    del user_sessions[user_id]
            
        except Exception as e:
            print(f"Error in cleanup task: {e}")
        
        await asyncio.sleep(CLEANUP_INTERVAL)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_all_sessions())

class Feedback(BaseModel):
    user_id: str | None = None
    user_feedback: str
    session_id: str | None = None

class Rating(BaseModel):
    response_id: str
    rating: str
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def rating_must_be_valid(cls, v):
        if v not in ["Helpful", "Not Helpful"]:
            raise ValueError("Rating must be 'Helpful' or 'Not Helpful'")
        return v

    @field_validator("comment")
    @classmethod
    def comment_required_for_not_helpful(cls, v, values):
        if values.data.get("rating") == "Not Helpful" and (v is None or v.strip() == ""):
            raise ValueError("Comment is required for 'Not Helpful' rating")
        return v

class FeedbackResponse(BaseModel):
    response_id: str
    user_id: str | None
    user_feedback: str
    ai_response: str
    timestamp: datetime
    status: str = "generated"
    session_id: str | None = None

class RatedFeedbackResponse(FeedbackResponse):
    rating: str | None = None
    comment: str | None = None
    improved_response: str | None = None
    llm_analysis: str | None = None
    locked: bool = False

def build_response_prompt(user_feedback: str, chat_history=None) -> str:
    if chat_history is None:
        chat_history = []
    history_str = ""
    for msg in chat_history:
        history_str += f"{msg['role']}: {msg['content']}\n"
    return f"""
            You are FitCoach, a friendly and knowledgeable fitness assistant dedicated to helping people achieve their health and fitness goals. You provide personalized advice on exercise routines, nutrition, and overall wellness. You're humble, encouraging, and always ready to learn from user feedback to improve your guidance.

            ### Your Personality:
            - Warm and supportive, like a trusted friend
            - Knowledgeable but never condescending
            - Focused on practical, achievable advice
            - Always safety-conscious
            - Encouraging and positive
            - Natural conversationalist who doesn't repeat the same questions
            - Adapts to user's communication style

            ### Chat History:
            {history_str}

            ### User's Question/Request:
            \"\"\"{user_feedback}\"\"\"

            ### Instructions:
            1. Provide clear, practical advice tailored to the user's needs
            2. Include specific examples and actionable steps
            3. Always emphasize safety and proper form
            4. Keep responses under 300 tokens
            5. End your response naturally:
            - If this is the first interaction, ask what specific fitness goals they have
            - If they've shared goals before, ask about their progress or if they have new questions
            - If they're asking for specific advice, offer to provide more details or alternatives
            6. If the user asks about exercises, include:
            - Proper form instructions
            - Common mistakes to avoid
            - Modifications for different fitness levels
            7. If the user asks about nutrition, include:
            - Practical meal suggestions
            - Portion guidance
            - Healthy alternatives
            8. If the user asks about workout planning, include:
            - Sample routines
            - Rest periods
            - Progression tips

            ### Conversation Flow:
            - Be natural and conversational
            - Don't repeatedly ask if information was helpful
            - If user says something was helpful, acknowledge it and move forward
            - If user needs more information, provide it without being asked
            - Show genuine interest in their progress and goals
            """

def build_improved_response_prompt(user_feedback: str, original_response: str, rating: str, comment: str) -> str:
    return f"""
You are FitCoach, a fitness assistant who learns from user feedback to provide better guidance. The user found your previous response '{rating}' and provided specific feedback. Use this feedback to create an improved, more helpful response.

### User's Original Question:
\"\"\"{user_feedback}\"\"\"

### Your Previous Response:
\"\"\"{original_response}\"\"\"

### User's Feedback:
\"\"\"{comment}\"\"\"

### Instructions:
1. Acknowledge the user's feedback naturally
2. Address specific points mentioned in their feedback
3. Provide more detailed or clearer information
4. Include practical examples and specific steps
5. Maintain a supportive and encouraging tone
6. End your response naturally:
   - If they found it helpful, thank them and ask about their next goal
   - If they need more info, provide it and ask if they have any other questions
   - If they're struggling, offer additional support or alternatives
7. If the feedback was about exercise advice:
   - Add more form details
   - Include visual cues
   - Provide alternative exercises
8. If the feedback was about nutrition:
   - Give more specific meal examples
   - Include portion sizes
   - Suggest meal prep tips
9. If the feedback was about workout planning:
   - Provide more detailed routines
   - Include rest/recovery guidance
   - Add progression strategies

### Conversation Style:
- Be natural and conversational
- Don't repeatedly ask if information was helpful
- Show genuine interest in their progress
- Adapt to their communication style
- Be supportive and encouraging
"""

def build_analysis_prompt(user_feedback: str, original_response: str, rating: str, comment: str) -> str:
    return f"""
            You are FitCoach's Quality Control Assistant. Analyze the interaction to help improve future responses.

            ### Instructions:
            1. Summarize the user's needs and feedback in one sentence
            2. Evaluate the response quality:
            - Was it practical and actionable?
            - Did it address safety concerns?
            - Was it appropriately detailed?
            - Was the conversation flow natural?
            - Did it avoid repetitive questions?
            3. Identify specific areas for improvement
            4. Suggest concrete ways to enhance the response
            5. Provide a one-word sentiment: Positive, Negative, or Neutral

            ### Example Output:
            - User Need Summary: The user needed clearer instructions for proper squat form
            - Response Evaluation: The response provided basic form but lacked safety cues and was too repetitive
            - Improvement Areas: Add common mistakes, visual cues, and make conversation more natural
            - Suggested Enhancements: Include step-by-step form guide with safety tips and more natural conversation flow
            - Sentiment Tag: Neutral

            ---

            🧠 User's Question:
            \"\"\"{user_feedback}\"\"\"
            🧠 FitCoach's Response:
            \"\"\"{original_response}\"\"\"
            ✅ User Rating: **{rating}**
            🗣 User Feedback: **\"{comment}\"\"\"
            """

async def call_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OpenAI API key not configured")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.2,
        "stop": ["---"]
            }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(OPENAI_API_URL, headers=headers, json=data, timeout=15)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {e}")

        try:
            result_json = response.json()
            if not result_json.get("choices") or not result_json["choices"][0].get("message"):
                raise HTTPException(status_code=500, detail="Invalid response structure from OpenAI API")
            return result_json["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse OpenAI API response: {e}")

@app.post("/generate-response", response_model=FeedbackResponse)
async def generate_response(feedback: Feedback):
    session_id = feedback.session_id
    user_id = feedback.user_id

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Initialize user's session dictionary if it doesn't exist
    if user_id not in user_sessions:
        user_sessions[user_id] = {}

    # Create new session if needed
    if not session_id:
        session_id = str(uuid.uuid4())
        user_sessions[user_id][session_id] = ChatSession(user_id=user_id)
    elif session_id not in user_sessions[user_id]:
        user_sessions[user_id][session_id] = ChatSession(user_id=user_id)
    
    session = user_sessions[user_id][session_id]

    # Add user message to history
    if not session.add_message("user", feedback.user_feedback):
        raise HTTPException(
            status_code=400,
            detail="Maximum message limit reached for this session"
        )

    # Generate AI response
    response_prompt = build_response_prompt(feedback.user_feedback, session.get_history())
    ai_response = await call_openai(response_prompt)
    
    # Add AI response to history
    if not session.add_message("assistant", ai_response):
        raise HTTPException(
            status_code=500,
            detail="Failed to store AI response in session history"
        )

    # Store response in memory
    response_id = str(uuid.uuid4())
    response_data = {
        "user_id": user_id,
        "user_feedback": feedback.user_feedback,
        "ai_response": ai_response,
        "timestamp": datetime.utcnow(),
        "status": "generated",
        "session_id": session_id
    }
    response_storage[response_id] = response_data

    return FeedbackResponse(response_id=response_id, **response_data)

@app.post("/rate-response", response_model=RatedFeedbackResponse)
async def rate_response(rating: Rating):
    # Retrieve stored response
    response_data = response_storage.get(rating.response_id)
    if not response_data:
        raise HTTPException(status_code=404, detail="Response not found")

    # Initialize response fields
    improved_response = None
    llm_analysis = None
    status = "confirmed"
    locked = False

    # Use empty string for comment if None
    comment = rating.comment or ""

    if rating.rating == "Not Helpful":
        # Generate improved response based on comment
        improved_prompt = build_improved_response_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        improved_response = await call_openai(improved_prompt)
        # Analyze feedback
        analysis_prompt = build_analysis_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        llm_analysis = await call_openai(analysis_prompt)
        status = "reviewed"
        locked = True  # Lock after generating improved response
    else:
        # For "Helpful", analyze feedback and lock
        analysis_prompt = build_analysis_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        llm_analysis = await call_openai(analysis_prompt)
        locked = True  # Lock after rating as "Helpful"

    # Update in-memory storage
    response_data.update({
        "rating": rating.rating,
        "comment": comment,
        "improved_response": improved_response,
        "llm_analysis": llm_analysis,
        "status": status,
        "locked": locked
    })

    return RatedFeedbackResponse(response_id=rating.response_id, **response_data)


from app.api.nutrition_router import router as nutrition_router
from app.api.workout_router import router as workout_router
from app.api.workout_calorie_calculation import router as workout_calorie_calculation_router
from app.api.reciept import router as reciept_router
from app.api.package_food_router import router as package_food_router


app.include_router(nutrition_router)
app.include_router(workout_router)
app.include_router(workout_calorie_calculation_router)

app.include_router(reciept_router, prefix="/receipt", tags=["Receipt Scanner"])
app.include_router(mealplan_router, tags=["MealPlan"])


app.include_router(package_food_router, prefix="/package-food", tags=["Packaged Food"])
