import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Session Configuration
SESSION_TIMEOUT = 3600  
MAX_SESSIONS_PER_USER = 5
MAX_MESSAGES_PER_SESSION = 50
CLEANUP_INTERVAL = 300  