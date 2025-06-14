from fastapi import APIRouter, HTTPException
from datetime import datetime
import uuid
from app.models.schemas import Feedback, Rating, FeedbackResponse, RatedFeedbackResponse
from app.services.session_manager import session_manager
from app.services.llm_service import llm_service

router = APIRouter()

@router.post("/generate-response", response_model=FeedbackResponse)
async def generate_response(feedback: Feedback):
    if not feedback.user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Get or create session
    session_id, session = session_manager.get_or_create_session(feedback.user_id, feedback.session_id)

    # Add user message to history
    if not session.add_message("user", feedback.user_feedback):
        raise HTTPException(
            status_code=400,
            detail="Maximum message limit reached for this session"
        )

    # Generate AI response
    response_prompt = llm_service.build_response_prompt(feedback.user_feedback, session.get_history())
    ai_response = await llm_service.generate_response(response_prompt)
    
    # Add AI response to history
    if not session.add_message("assistant", ai_response):
        raise HTTPException(
            status_code=500,
            detail="Failed to store AI response in session history"
        )

    # Store response in memory
    response_id = str(uuid.uuid4())
    response_data = {
        "user_id": feedback.user_id,
        "user_feedback": feedback.user_feedback,
        "ai_response": ai_response,
        "timestamp": datetime.utcnow(),
        "status": "generated",
        "session_id": session_id
    }
    session_manager.store_response(response_id, response_data)

    return FeedbackResponse(response_id=response_id, **response_data)

@router.post("/rate-response", response_model=RatedFeedbackResponse)
async def rate_response(rating: Rating):
    # Retrieve stored response
    response_data = session_manager.get_response(rating.response_id)
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
        improved_prompt = llm_service.build_improved_response_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        improved_response = await llm_service.generate_response(improved_prompt)
        # Analyze feedback
        analysis_prompt = llm_service.build_analysis_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        llm_analysis = await llm_service.generate_response(analysis_prompt)
        status = "reviewed"
        locked = True  # Lock after generating improved response
    else:
        # For "Helpful", analyze feedback and lock
        analysis_prompt = llm_service.build_analysis_prompt(
            response_data["user_feedback"],
            response_data["ai_response"],
            rating.rating,
            comment
        )
        llm_analysis = await llm_service.generate_response(analysis_prompt)
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