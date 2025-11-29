from fastapi import APIRouter, UploadFile
from app.services.receipt_scanner import ReceiptScanner

router = APIRouter()
scanner = ReceiptScanner()

@router.post("/scan")
async def scan_receipt(user_id: str, file: UploadFile):
    path = f"temp_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())

    data = scanner.scan_receipt(path, user_id)
    return {"status": "success", "data": data}


@router.get("/user/{user_id}/receipts")
def get_receipts(user_id: str):
    return scanner.get_user_receipts(user_id)