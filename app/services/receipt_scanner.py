import base64
import json
from enum import Enum
from typing import List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from collections import defaultdict
from app.config import settings

load_dotenv()


# ─────────────────────────────────────────────────────────────
# ENUM: Categories
# ─────────────────────────────────────────────────────────────
class FoodCategory(str, Enum):
    FRUITS = "Fruits"
    VEGETABLES = "Vegetables"
    DAIRY = "Dairy"
    MEAT_POULTRY = "Meat & Poultry"
    FISH_SEAFOOD = "Fish & Seafood"
    GRAINS_CEREALS = "Grains & Cereals"
    SNACKS_PACKAGED = "Snacks & Packaged Foods"
    BEVERAGES = "Beverages"
    FROZEN_FOODS = "Frozen Foods"
    BAKERY = "Bakery"
    CONDIMENTS_SPICES = "Condiments & Spices"
    OTHER = "Other / Miscellaneous"


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────
class Product(BaseModel):
    name: str
    cost: str
    quantity: str
    total_cost: str


class Category(BaseModel):
    category_name: FoodCategory
    products: List[Product] = Field(default_factory=list)
    total_price: str


class ReceiptAnalysisResponse(BaseModel):
    store_name: str = "Unknown"
    receipt_date: str = "Unknown"
    categories: List[Category]
    grand_total: str
    tax_amount: str = "0.00"
    subtotal: str = "0.00"


# ─────────────────────────────────────────────────────────────
# LLM Prompt
# ─────────────────────────────────────────────────────────────
RECEIPT_CATEGORIZATION_PROMPT = """
You are an expert at analyzing grocery receipts and categorizing food items. 

Your Task:
Analyze the receipt image and extract all products, then categorize each product into one of the predefined categories.

Rules:
1. Extract EVERY item line including items with weights, specials, or multi-buy.
2. If quantity missing → assume "1".
3. If cost missing → use total_cost for both.
4. Keep units inside the product name (e.g., “200g”, “1L”, “500 ml”).
5. Prices must always be string numbers with 2 decimal places.
6. DO NOT invent items. Only extract what's visible.
7. Extract store name, date, subtotal, tax, and grand total.
8. Return ONLY valid JSON following the schema. No explanations.
"""


# ─────────────────────────────────────────────────────────────
# Receipt Scanner Class
# ─────────────────────────────────────────────────────────────
class ReceiptScanner:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY missing")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
        self.data_dir = Path("receipt_data")
        self.data_dir.mkdir(exist_ok=True)

    # Encode image to Base64
    def encode_image(self, path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    # ─────────────────────────────────────────────────────────
    # Run Analysis
    # ─────────────────────────────────────────────────────────
    def scan_receipt(self, image_path, user_id):
        image_base64 = self.encode_image(image_path)

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": RECEIPT_CATEGORIZATION_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this receipt image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
                            }
                        },
                    ],
                },
            ],
            response_format=ReceiptAnalysisResponse,
        )

        parsed = response.choices[0].message.parsed
        data = parsed.dict()

        # Add metadata
        data["user_id"] = user_id
        data["scan_timestamp"] = datetime.now().isoformat()
        data["image_path"] = str(image_path)

        self._save_receipt(user_id, data)
        return data

    # ─────────────────────────────────────────────────────────
    # Save JSON
    # ─────────────────────────────────────────────────────────
    def _save_receipt(self, user_id, data):
        file = self.data_dir / f"user_{user_id}.json"

        if file.exists():
            user_data = json.load(open(file))
        else:
            user_data = {"user_id": user_id, "receipts": []}

        user_data["receipts"].append(data)
        json.dump(user_data, open(file, "w"), indent=2)

    # ─────────────────────────────────────────────────────────
    # Get Receipts
    # ─────────────────────────────────────────────────────────
    def get_user_receipts(self, user_id):
        file = self.data_dir / f"user_{user_id}.json"
        if not file.exists():
            return {"user_id": user_id, "receipts": []}
        return json.load(open(file))