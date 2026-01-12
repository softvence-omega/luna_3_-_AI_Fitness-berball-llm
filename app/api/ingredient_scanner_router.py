from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ingredient_scanner_service import scan_ingredients, IngredientListResponse

router = APIRouter(
    prefix="/ingredient-scanner",
    tags=["Ingredient Scanner"]
)

@router.post("/", response_model=IngredientListResponse)
async def scan_food_ingredients(file: UploadFile = File(...)):
    """
    Scan an image of food (raw or packaged) to get a list of ingredients.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        image_bytes = await file.read()
        response = await scan_ingredients(image_bytes)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
