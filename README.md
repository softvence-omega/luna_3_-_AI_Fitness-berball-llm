# Barbell AI Fitness System

A FastAPI-based system for managing AI-powered fitness coaching, nutrition analysis, workout planning, and feedback with robust session management.

## Project Structure

```
app/
├── api/
│   ├── endpoints.py                  # Feedback and rating API endpoints
│   ├── nutrition_router.py           # Nutrition analysis endpoints
│   ├── workout_router.py             # Workout plan endpoints
│   ├── workout_calorie_calculation.py# Calorie calculation endpoints
│   └── separate.py                   # (Untracked/experimental)
├── config/
│   └── settings.py                   # Configuration settings
├── models/
│   ├── nutrition_schema.py           # Nutrition response schemas
│   ├── schemas.py                    # Feedback, rating, and response schemas
│   ├── session.py                    # Session model
│   └── workout_schema.py             # Workout schemas
├── services/
│   ├── llm_service.py                # LLM (OpenAI) interaction service
│   ├── nutrition_service.py          # Nutrition analysis logic
│   ├── session_manager.py            # Session management logic
│   ├── workout_calorie_burn_calculation.py # Calorie calculation logic
│   └── workout_service.py            # Workout plan generation logic
└── main.py                           # Application entry point
```

## Features

- AI-powered feedback and response system
- Personalized workout plan generation and refinement
- Nutrition analysis from meal images
- Calorie burn calculation for exercises
- Session management with automatic cleanup
- User-based session organization
- Response rating and improvement system
- Automatic session cleanup every 5 minutes
- Extensible, modular service architecture

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

3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

### Feedback & Session
- `POST /generate-response`: Generate AI response for user feedback (with session management)
- `POST /rate-response`: Rate and provide feedback for AI responses

### Nutrition
- `POST /analyze-meal-nutrition`: Analyze nutritional content of a meal from an uploaded image

### Workout
- `POST /create-workout-plan`: Generate a personalized workout plan
- `POST /update-workout-plan`: Update/refine a workout plan based on user feedback

### Calorie Calculation
- `POST /workout-calorie/calculate-calories`: Calculate calories burned for an exercise session
- `GET  /workout-calorie/`: Calorie Calculator API info
- `GET  /workout-calorie/health`: Health check

## Data Models

### Feedback & Rating
- **Feedback**: `{ user_id, user_feedback, session_id }`
- **Rating**: `{ response_id, rating ("Helpful"|"Not Helpful"), comment }`
- **FeedbackResponse**: `{ response_id, user_id, user_feedback, ai_response, timestamp, status, session_id }`
- **RatedFeedbackResponse**: Extends FeedbackResponse with rating, comment, improved_response, llm_analysis, locked

### Nutrition
- **NutritionResponse**: `{ total_protein_g, total_carbs_g, total_fats_g, total_fiber_g, total_calories }`

### Workout
- **WorkoutPlanRequest**: `{ age, gender, weight_kg, height_cm, fitness_level, main_goal, days_per_week, available_equipment, notes }`
- **WorkoutPlanResponse**: `{ workout_plan: { plan: [ { day, focus, exercises: [ { name, sets, reps, rest_period_minutes } ] } ] } }`
- **WorkoutUpdateRequest**: `{ original_plan, feedback }`
- **ExerciseRequest**: `{ body_weight, height, exerciseName, exerciseType, exerciseDescription, resetTime, weightLifted, reps, sets, restTime }`
- **CalorieResponse**: `{ total_calories_burned, exercise_details }`

## Session Management

- Sessions are organized by user ID
- Each user can have multiple sessions (max 5)
- Sessions expire after 1 hour of inactivity
- System cleans up expired sessions every 5 minutes
- Maximum 50 messages per session

## Technology Stack
- **FastAPI** for API framework
- **Pydantic** for data validation
- **OpenAI GPT (via LangChain)** for AI responses
- **LangChain** for advanced LLM orchestration
- **Python-dotenv** for environment management

## Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](LICENSE)