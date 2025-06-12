from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator, field_validator
import httpx
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid
import asyncio
from typing import Dict, Optional

load_dotenv()

app = FastAPI()

# Load Groq API key from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

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
        if values.get("rating") == "Not Helpful" and (v is None or v.strip() == ""):
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
You are an AI assistant providing helpful and accurate responses. Based on the user's feedback and the chat history, generate a clear and relevant response. If the feedback is about a technical topic like FastAPI, include specific code examples where applicable.

### Chat History:
{history_str}

### User Feedback:
\"\"\"{user_feedback}\"\"\"
### Instructions:
- Provide a concise, accurate, and relevant response.
- If the feedback involves a technical query (e.g., FastAPI), include a code example like a route or async function.
- Keep the response under 300 tokens.
"""

def build_improved_response_prompt(user_feedback: str, original_response: str, rating: str, comment: str) -> str:
    return f"""
You are an AI assistant tasked with improving a previous response based on user feedback, rating, and a specific comment. The original response was rated '{rating}', indicating it was not helpful. Use the user's comment to address specific issues and generate an improved response that is clear, relevant, and includes specific details or code examples (e.g., FastAPI routes) if applicable.

### User Feedback:
\"\"\"{user_feedback}\"\"\"
### Original Response:
\"\"\"{original_response}\"\"\"
### User Comment:
\"\"\"{comment}\"\"\"
### Instructions:
- Address the issues raised in the comment.
- If the comment suggests missing examples, include relevant code snippets (e.g., FastAPI routes or async functions).
- Keep the response concise and focused.
"""

def build_analysis_prompt(user_feedback: str, original_response: str, rating: str, comment: str) -> str:
    return f"""
You are an AI Quality Control Assistant. Analyze the user's feedback, the AI-generated response, the rating, and the comment with the following objectives:

### Instructions:
1. Summarize the user's sentiment in one concise sentence.
2. Evaluate the quality of the AI response, noting strengths and weaknesses.
3. Suggest specific, actionable improvements, including relevant FastAPI code examples if applicable (e.g., routes, async endpoints).
4. Conclude with a one-word sentiment tag: Positive, Negative, or Neutral.
5. Keep the response concise and focused.

### Example Output:
- User Sentiment Summary: The user found the response unhelpful due to missing examples.
- Response Evaluation: The response explained FastAPI but lacked practical examples.
- Suggested Improvements: Include a FastAPI route, e.g., `@app.get('/') async def read_root(): return {{'message': 'Hello, World!'}}`.
- Sentiment Tag: Negative

---

🧠 User Feedback:
\"\"\"{user_feedback}\"\"\"
🧠 AI Response:
\"\"\"{original_response}\"\"\"
✅ User Rating: **{rating}**
🗣 Comment: **\"{comment}\"\"\"
"""

async def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise HTTPException(status_code=400, detail="Groq API key not configured")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 300,
        "temperature": 0.3,
        "stop": ["---"]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(GROQ_API_URL, headers=headers, json=data, timeout=15)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Groq API request failed: {e}")

        try:
            result_json = response.json()
            if not result_json.get("choices") or not result_json["choices"][0].get("message"):
                raise HTTPException(status_code=500, detail="Invalid response structure from Groq API")
            return result_json["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise HTTPException(status_code=500, detail=f"Failed to parse Groq API response: {e}")

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
    ai_response = await call_groq(response_prompt)
    
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
        improved_response = await call_groq(improved_prompt)
        # Analyze feedback
        analysis_prompt = build_analysis_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        llm_analysis = await call_groq(analysis_prompt)
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
        llm_analysis = await call_groq(analysis_prompt)
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


    