from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.nutrition_router import router as nutrition_router
from app.api.workout_router import router as workout_router
from app.api.workout_calorie_calculation import router as workout_calorie_calculation_router


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://luna3server.onrender.com/api/v1", "http://127.0.0.1:8000", "http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(nutrition_router)
app.include_router(workout_router)
app.include_router(workout_calorie_calculation_router)

@app.get("/")
async def root():
    return {
        "message": "Calorie Calculator API",
        "version": "1.0.0",
        "endpoints": {
            "POST /workout-calorie/calculate-calories": "Calculate calories burned for an exercise session"
        }
    }
