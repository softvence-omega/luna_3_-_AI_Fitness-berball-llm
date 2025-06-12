from typing import Dict
import asyncio
from datetime import datetime
from app.models.session import ChatSession
from app.config.settings import CLEANUP_INTERVAL
import uuid

class SessionManager:
    def __init__(self):
        self.user_sessions: Dict[str, Dict[str, ChatSession]] = {}
        self.response_storage: Dict[str, dict] = {}

    async def cleanup_all_sessions(self):
        while True:
            try:
                # Clean up expired sessions for each user
                for user_id in list(self.user_sessions.keys()):
                    user_session_dict = self.user_sessions[user_id]
                    
                    # Remove expired sessions
                    expired_sessions = [
                        session_id for session_id, session in user_session_dict.items()
                        if session.is_expired()
                    ]
                    for session_id in expired_sessions:
                        del user_session_dict[session_id]
                    
                    # If user has no sessions left, remove the user entry
                    if not user_session_dict:
                        del self.user_sessions[user_id]
                
            except Exception as e:
                print(f"Error in cleanup task: {e}")
            
            await asyncio.sleep(CLEANUP_INTERVAL)

    def get_or_create_session(self, user_id: str, session_id: str | None = None) -> tuple[str, ChatSession]:
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {}

        if not session_id:
            session_id = str(uuid.uuid4())
            self.user_sessions[user_id][session_id] = ChatSession(user_id=user_id)
        elif session_id not in self.user_sessions[user_id]:
            self.user_sessions[user_id][session_id] = ChatSession(user_id=user_id)

        return session_id, self.user_sessions[user_id][session_id]

    def store_response(self, response_id: str, response_data: dict):
        self.response_storage[response_id] = response_data

    def get_response(self, response_id: str) -> dict | None:
        return self.response_storage.get(response_id)

# Create a singleton instance
session_manager = SessionManager() 