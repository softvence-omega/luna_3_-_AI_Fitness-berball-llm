from datetime import datetime
from typing import List, Dict, Optional

class ChatSession:
    def __init__(self, user_id: Optional[str] = None):
        self.history: List[Dict[str, str]] = []
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.message_count = 0

    def add_message(self, role: str, content: str) -> bool:
        if self.message_count >= 50:  # MAX_MESSAGES_PER_SESSION
            return False
        
        self.history.append({"role": role, "content": content})
        self.last_activity = datetime.utcnow()
        self.message_count += 1
        return True

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def is_expired(self) -> bool:
        return (datetime.utcnow() - self.last_activity).total_seconds() > 3600  # SESSION_TIMEOUT

    def clear(self) -> None:
        self.history = []
        self.message_count = 0 