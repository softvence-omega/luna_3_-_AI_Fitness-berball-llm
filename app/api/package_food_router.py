from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services import nutrition_service
from app.services.package_food_ingredients import PackagedFoodResponse,  scan_packaged_food


router = APIRouter(
    tags=["Packaged Food"],
)

@router.post("/analyze-packaged-food", response_model=PackagedFoodResponse)
async def analyze_packaged_food(image: UploadFile = File(...)):
    
    try:
        content = await image.read()
        return await scan_packaged_food(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred during nutrition analysis.")
