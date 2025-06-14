import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Session Configuration
SESSION_TIMEOUT = 3600  # 1 hour in seconds
MAX_SESSIONS_PER_USER = 5
MAX_MESSAGES_PER_SESSION = 50
CLEANUP_INTERVAL = 300  # 5 minutes in seconds 