from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional

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