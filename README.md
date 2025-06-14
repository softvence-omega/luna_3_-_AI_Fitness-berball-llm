# AI Feedback System

A FastAPI-based system for managing AI feedback and responses with session management.

## Project Structure

```
app/
├── api/
│   └── endpoints.py      # API route handlers
├── config/
│   └── settings.py       # Configuration settings
├── models/
│   ├── schemas.py        # Pydantic models
│   └── session.py        # Session model
├── services/
│   ├── llm_service.py    # LLM interaction service
│   └── session_manager.py # Session management service
└── main.py              # Application entry point
```

## Features

- Session management with automatic cleanup
- User-based session organization
- AI response generation and feedback
- Response rating and improvement system
- Automatic session cleanup every 5 minutes

## Setup

1. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Groq API key:
```
GROQ_API_KEY=your_api_key_here
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /api/v1/generate-response`: Generate AI response for user feedback
- `POST /api/v1/rate-response`: Rate and provide feedback for AI responses

## Session Management

- Sessions are organized by user ID
- Each user can have multiple sessions
- Sessions automatically expire after 1 hour of inactivity
- System cleans up expired sessions every 5 minutes
- Maximum 50 messages per session
- Maximum 5 sessions per user 